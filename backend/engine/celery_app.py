import os
import asyncio
from celery import Celery
from engine.oasis_engine import OasisEngine

REDIS_URL_BASE = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_URL = f"{REDIS_URL_BASE}/{REDIS_DB}"

celery_app = Celery("aurapulse", broker=REDIS_URL, backend=REDIS_URL)

@celery_app.task(bind=True)
def run_dual_swarm(self, postA: str, postB: str, simulation_id: str, agent_count: int = 20):
    engine = OasisEngine()
    
    async def run_both():
        # Fire off both tracks in parallel, passing the requested count
        await asyncio.gather(
            engine.run_simulation("TrackA", postA, simulation_id=simulation_id, turns=2, agent_count=agent_count),
            engine.run_simulation("TrackB", postB, simulation_id=simulation_id, turns=2, agent_count=agent_count)
        )
    
    asyncio.run(run_both())
    return f"Finished Dual Swarm for {simulation_id} with {agent_count} agents"
