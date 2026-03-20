import os
import json
import redis.asyncio as aioredis
import random
import asyncio
from typing import List, Dict
from engine.agent import generate_agent_response_async
from graph.retriever import get_context_for_post
from dotenv import load_dotenv

# Load global config first
CONFIG_PATH = os.path.expanduser("~/.aura/aura.cfg")
print(f"DEBUG: OasisEngine loading config from {CONFIG_PATH}, exists: {os.path.exists(CONFIG_PATH)}")
load_dotenv(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else load_dotenv("/app/.aura/aura.cfg")

REDIS_URL_BASE = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_URL = f"{REDIS_URL_BASE}/{REDIS_DB}"

# Global lock for file operations to prevent race conditions during scaling
persona_lock = asyncio.Lock()

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
            # 1. Load grounded personas with lock
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "personas.json")
            print(f"DEBUG: [{track_id}] Loading personas from: {file_path}")
            
            async with persona_lock:
                all_personas = []
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        all_personas = json.load(f)
                
                # Dynamic Swarm Scaling
                if agent_count > len(all_personas):
                    print(f"[{track_id}] Scaling swarm from {len(all_personas)} to {agent_count}...")
                    await redis_client.publish('sim_stream', json.dumps({"type": "status", "message": "Generating Personas..."}))
                    from engine.personas import get_grounding_concepts, create_persona_llm
                    concepts = get_grounding_concepts(client_id=self.app_env)
                    
                    needed = agent_count - len(all_personas)
                    semaphore = asyncio.Semaphore(4)
                    async def sem_create():
                        async with semaphore:
                            return await create_persona_llm(concepts)
                    
                    tasks = [sem_create() for _ in range(needed)]
                    new_personas = await asyncio.gather(*tasks)
                    all_personas.extend(new_personas)
                    
                    with open(file_path, "w") as f:
                        json.dump(all_personas, f, indent=2)

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
