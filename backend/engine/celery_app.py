import os
import asyncio
from celery import Celery
from engine.oasis_engine import OasisEngine
from api.config import settings

celery_app = Celery("aurapulse", broker=settings.redis_full_url, backend=settings.redis_full_url)

@celery_app.task(bind=True)
def run_single_swarm(self, track_id: str, post_text: str, simulation_id: str, agent_count: int = 10):
    engine = OasisEngine()
    
    async def run_it():
        await engine.run_simulation(track_id, post_text, simulation_id=simulation_id, turns=2, agent_count=agent_count)
    
    asyncio.run(run_it())
    return f"Finished {track_id} for {simulation_id}"
