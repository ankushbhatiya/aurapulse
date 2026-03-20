import os
import json
import redis.asyncio as aioredis
import random
import asyncio
from typing import List, Dict
from engine.agent import generate_agent_response_async
from graph.retriever import get_context_for_post
REDIS_URL_BASE = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_URL = f"{REDIS_URL_BASE}/{REDIS_DB}"

class OasisEngine:
    def __init__(self):
        self.redis_url = REDIS_URL
        self.semaphore = None
        self.app_env = os.getenv("APP_ENV", "development")

    async def run_simulation(self, track_id: str, post_text: str, simulation_id: str, turns: int = 2, agent_count: int = 20):
        """
        Orchestrates a multi-turn OASIS simulation in parallel with a semaphore limit.
        """
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(5)

        redis_client = aioredis.from_url(self.redis_url)

        try:
            # 1. Load grounded personas
            file_path = os.path.join(os.path.dirname(__file__), "personas.json")
            with open(file_path, "r") as f:
                all_personas = json.load(f)

            # Use only the requested number of agents
            if agent_count > len(all_personas):
                print(f"Warning: Requested {agent_count} agents but only {len(all_personas)} available.")
                personas = all_personas
            else:
                personas = random.sample(all_personas, agent_count)

            # 2. Get Knowledge Graph Context (passing app_env as tenant_id)
            context = get_context_for_post(post_text, client_id=self.app_env)
            
            # Track simulation history
            simulation_history = []

            for turn in range(1, turns + 1):
                print(f"[{track_id}] Starting Turn {turn} ({len(personas)} agents)...")
                
                # Shuffle active personas for this turn
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
                    "total_expected": total_expected # Pass to UI for progress bar
                }
                
                await redis_client.publish('sim_stream', json.dumps(message))
                await redis_client.rpush(f"logs:{simulation_id}:{track_id}", json.dumps(message))
                
                return message
            except Exception as e:
                print(f"Error processing agent {persona['name']}: {e}")
                return None
