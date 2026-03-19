import os
import json
import redis
from celery import Celery
from engine.agent import generate_agent_response
from graph.retriever import get_context_for_post

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("aurapulse", broker=REDIS_URL, backend=REDIS_URL)

redis_client = redis.Redis.from_url(REDIS_URL)

@celery_app.task
def run_swarm(track_id: str, post_text: str):
    # 1. Load personas
    file_path = os.path.join(os.path.dirname(__file__), "personas.json")
    with open(file_path, "r") as f:
        personas = json.load(f)
    
    # 2. Get Knowledge Graph Context
    context = get_context_for_post(post_text)
    
    # 3. Iterate through swarm
    for persona in personas:
        # Generate the AI agent comment
        comment = generate_agent_response(persona, post_text, context)
        
        # 4. Stream result to Redis Pub/Sub for the UI to catch
        message = {
            "track_id": track_id,
            "persona_name": persona["name"],
            "bias": persona["bias"],
            "comment": comment
        }
        redis_client.publish('sim_stream', json.dumps(message))
    
    return f"Finished Swarm for {track_id}"
