import os
import asyncio
from celery import Celery
from engine.oasis_engine import OasisEngine
from api.config import settings

celery_app = Celery("aurapulse", broker=settings.redis_full_url, backend=settings.redis_full_url)

@celery_app.task(bind=True)
def run_dual_swarm(self, postA: str, postB: str, simulation_id: str, agent_count: int = 20):
    engine = OasisEngine()
    
    async def run_both():
        await asyncio.gather(
            engine.run_simulation("TrackA", postA, simulation_id=simulation_id, turns=2, agent_count=agent_count),
            engine.run_simulation("TrackB", postB, simulation_id=simulation_id, turns=2, agent_count=agent_count)
        )
    
    asyncio.run(run_both())
    return f"Finished Dual Swarm for {simulation_id} with {agent_count} agents"
