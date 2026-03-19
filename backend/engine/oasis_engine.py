import os
import json
import redis
import random
from typing import List, Dict
from engine.agent import generate_agent_response
from graph.retriever import get_context_for_post

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class OasisEngine:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(REDIS_URL)

    def run_simulation(self, track_id: str, post_text: str, turns: int = 2):
        """
        Orchestrates a multi-turn OASIS simulation.
        - Turn 1: Agents react to the main post.
        - Turn 2+: Agents react to the main post OR high-engagement comments.
        """
        # 1. Load grounded personas
        file_path = os.path.join(os.path.dirname(__file__), "personas.json")
        with open(file_path, "r") as f:
            personas = json.load(f)
        
        # 2. Get Knowledge Graph Context
        context = get_context_for_post(post_text)
        
        # Track simulation history for intra-swarm awareness
        simulation_history = []

        for turn in range(1, turns + 1):
            print(f"[{track_id}] Starting Turn {turn}...")
            
            # Shuffle personas for each turn to simulate async behavior
            active_personas = random.sample(personas, len(personas))
            
            for persona in active_personas:
                # Turn 1: Always main post
                # Turn 2+: 50% chance to reply to a previous comment if history exists
                reply_to = None
                target_text = post_text
                
                if turn > 1 and simulation_history and random.random() > 0.5:
                    reply_to = random.choice(simulation_history)
                    target_text = f"User {reply_to['persona_name']} said: '{reply_to['comment']}' in response to the post: '{post_text}'"

                # Generate agent comment
                comment = generate_agent_response(persona, target_text, context)
                
                message = {
                    "track_id": track_id,
                    "turn": turn,
                    "persona_name": persona["name"],
                    "bias": persona["bias"],
                    "comment": comment,
                    "reply_to": reply_to["persona_name"] if reply_to else None
                }
                
                # Store in history for other agents to see
                simulation_history.append(message)
                
                # Stream result to UI
                self.redis_client.publish('sim_stream', json.dumps(message))
                
        return f"Finished OASIS Swarm for {track_id}"

if __name__ == "__main__":
    engine = OasisEngine()
    engine.run_simulation("TestTrack", "Should we switch to 100% sustainable fashion?")
