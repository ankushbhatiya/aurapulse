import os
from celery import Celery
from engine.oasis_engine import OasisEngine

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("aurapulse", broker=REDIS_URL, backend=REDIS_URL)

@celery_app.task
def run_swarm(track_id: str, post_text: str):
    engine = OasisEngine()
    # Run a 2-turn simulation for POC speed
    return engine.run_simulation(track_id, post_text, turns=2)
