import os
import json
import redis.asyncio as aioredis
import random
import asyncio
from typing import List, Dict
from engine.agent import generate_agent_response_async
from graph.retriever import get_context_for_post
from api.config import settings

class OasisEngine:
    def __init__(self):
        self.redis_url = settings.redis_full_url
        self.semaphore = None
        self.app_env = settings.APP_ENV
        self._persona_lock = None

    @property
    def persona_lock(self):
        if self._persona_lock is None:
            self._persona_lock = asyncio.Lock()
        return self._persona_lock

    async def run_simulation(self, track_id: str, post_text: str, simulation_id: str, turns: int = 2, agent_count: int = 20):
        """
        Orchestrates a multi-turn OASIS simulation in parallel with a semaphore limit.
        """
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(50)

        redis_client = aioredis.from_url(self.redis_url)
        
        try:
            # 1. Load grounded personas with lock
            from engine.personas import load_personas_from_redis
            
            async with self.persona_lock:
                all_personas = await load_personas_from_redis(client_id=self.app_env)
                
                # Dynamic Swarm Scaling
                if agent_count > len(all_personas):
                    print(f"[{track_id}] Scaling swarm from {len(all_personas)} to {agent_count}...")
                    await redis_client.publish('sim_stream', json.dumps({"type": "status", "message": "Generating Personas..."}))
                    from engine.personas import get_grounding_concepts, create_persona_llm
                    concepts = await get_grounding_concepts(client_id=self.app_env)
                    
                    needed = agent_count - len(all_personas)
                    semaphore = asyncio.Semaphore(4)
                    async def sem_create(i):
                        async with semaphore:
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
                print(f"DEBUG: [{track_id}] Swarm size finalized at: {len(personas)} agents.")

            # 2. Get Knowledge Graph Context
            context = get_context_for_post(post_text, client_id=self.app_env)
            
            simulation_history = []
            
            await redis_client.publish('sim_stream', json.dumps({"type": "status", "message": "Running Swarm..."}))

            for turn in range(1, turns + 1):
                print(f"[{track_id}] Starting Turn {turn} ({len(personas)} agents)...")
                
                active_personas = random.sample(personas, len(personas))
                
                tasks = []
                for persona in active_personas:
                    reply_to = None
                    target_text = post_text
                    
                    if turn > 1 and simulation_history and random.random() > 0.5:
                        reply_to = random.choice(simulation_history)
                        target_text = f"User {reply_to['persona_name']} said: '{reply_to['comment']}' in response to the post: '{post_text}'"

                    tasks.append(self._process_agent_turn(redis_client, persona, target_text, context, simulation_id, track_id, turn, reply_to, len(personas) * turns))

                turn_results = await asyncio.gather(*tasks)
                simulation_history.extend([r for r in turn_results if r])
                    
            return f"Finished OASIS Swarm for {simulation_id}:{track_id}"
        finally:
            await redis_client.aclose()

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
                
                await redis_client.publish('sim_stream', json.dumps(message))
                await redis_client.rpush(f"logs:{simulation_id}:{track_id}", json.dumps(message))
                return message
            except Exception as e:
                print(f"Error processing agent {persona['name']}: {e}")
                return None

if __name__ == "__main__":
    engine = OasisEngine()
    asyncio.run(engine.run_simulation("TestTrack", "Async test!", "manual_test"))
