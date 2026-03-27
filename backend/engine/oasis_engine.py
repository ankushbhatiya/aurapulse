import os
import json
import asyncio
import random
from typing import List, Dict
from engine.agent import generate_agent_response_async
from graph.retriever import get_context_for_post
from api.config import settings
from api.logger import logger
from api.redis_utils import redis_manager

class OasisEngine:
    def __init__(self):
        self.semaphore = None
        self.app_env = settings.APP_ENV

    async def run_simulation(self, track_id: str, post_text: str, simulation_id: str, turns: int = 2, agent_count: int = 20):
        """
        Orchestrates a multi-turn OASIS simulation in parallel with a semaphore limit.
        """
        if self.semaphore is None:
            # Load from settings or default to 50
            limit = getattr(settings, "CONCURRENT_AGENT_LIMIT", 50)
            self.semaphore = asyncio.Semaphore(limit)

        redis_client = redis_manager.get_client()
        
        try:
            # 1. Load grounded personas
            from engine.personas import load_personas_from_redis
            
            # Using a distributed lock for persona generation/scaling
            async with redis_client.lock(f"lock:personas:{self.app_env}", timeout=60):
                all_personas = await load_personas_from_redis(client_id=self.app_env)
                
                # Dynamic Swarm Scaling
                if agent_count > len(all_personas):
                    logger.info(f"[{track_id}] Scaling swarm from {len(all_personas)} to {agent_count}...")
                    status_msg = json.dumps({"type": "status", "message": "Generating Personas...", "simulation_id": simulation_id})
                    await redis_client.publish('sim_stream', status_msg)
                    await redis_client.publish(f'sim_stream:{simulation_id}', status_msg)
                    
                    from engine.personas import get_grounding_concepts, create_persona_llm
                    concepts = await get_grounding_concepts(client_id=self.app_env)
                    
                    needed = agent_count - len(all_personas)
                    # Use a smaller semaphore for LLM persona generation to avoid rate limits
                    gen_semaphore = asyncio.Semaphore(4)
                    
                    async def sem_create(i):
                        async with gen_semaphore:
                            return await create_persona_llm(concepts, unique_id=i)
                    
                    tasks = [sem_create(i) for i in range(needed)]
                    new_batch = await asyncio.gather(*tasks)
                    
                    # Uniqueness check before adding
                    seen_names = {p["name"] for p in all_personas}
                    import uuid
                    for p in new_batch:
                        if p["name"] in seen_names:
                            p["name"] = f"{p['name']} ({uuid.uuid4().hex[:4]})"
                        all_personas.append(p)
                        seen_names.add(p["name"])
                    
                    # Update Redis
                    await redis_client.set(f"personas:{self.app_env}", json.dumps(all_personas))

                personas = random.sample(all_personas, agent_count)
                logger.debug(f"[{track_id}] Swarm size finalized at: {len(personas)} agents.")

            # 2. Get Knowledge Graph Context
            context = get_context_for_post(post_text, client_id=self.app_env)
            
            simulation_history = []
            
            status_running = json.dumps({"type": "status", "message": "Running Swarm...", "simulation_id": simulation_id})
            await redis_client.publish('sim_stream', status_running)
            await redis_client.publish(f'sim_stream:{simulation_id}', status_running)

            for turn in range(1, turns + 1):
                logger.info(f"[{track_id}] Starting Turn {turn} ({len(personas)} agents)...")
                
                # Shuffle personas for each turn
                active_personas = random.sample(personas, len(personas))
                
                tasks = []
                for persona in active_personas:
                    reply_to = None
                    target_text = post_text
                    
                    # 50% chance to reply to a previous comment if not first turn
                    if turn > 1 and simulation_history and random.random() > 0.5:
                        reply_to = random.choice(simulation_history)
                        target_text = f"User {reply_to['persona_name']} said: '{reply_to['comment']}' in response to the post: '{post_text}'"

                    tasks.append(self._process_agent_turn(redis_client, persona, target_text, context, simulation_id, track_id, turn, reply_to, len(personas) * turns))

                turn_results = await asyncio.gather(*tasks)
                simulation_history.extend([r for r in turn_results if r])
                    
            return f"Finished OASIS Swarm for {simulation_id}:{track_id}"
        except Exception as e:
            logger.error(f"Simulation failed for {simulation_id}:{track_id}: {e}", exc_info=True)
            return f"Failed OASIS Swarm for {simulation_id}:{track_id}"

    async def _process_agent_turn(self, redis_client, persona, target_text, context, simulation_id, track_id, turn, reply_to, total_expected):
        async with self.semaphore:
            try:
                comment = await generate_agent_response_async(persona, target_text, context, sim_id=simulation_id)
                
                message = {
                    "simulation_id": simulation_id,
                    "track_id": track_id,
                    "turn": turn,
                    "persona_name": persona["name"],
                    "bias": persona["bias"],
                    "comment": comment,
                    "reply_to": reply_to["persona_name"] if reply_to else None,
                    "total_expected": total_expected
                }
                
                msg_json = json.dumps(message)
                await redis_client.publish('sim_stream', msg_json)
                await redis_client.publish(f'sim_stream:{simulation_id}', msg_json)
                await redis_client.rpush(f"logs:{simulation_id}:{track_id}", msg_json)
                return message
            except Exception as e:
                logger.error(f"Error processing agent {persona['name']}: {e}")
                return None

if __name__ == "__main__":
    engine = OasisEngine()
    # In a real script we would need to handle the redis connection lifecycle
    # asyncio.run(engine.run_simulation("TestTrack", "Async test!", "manual_test"))
