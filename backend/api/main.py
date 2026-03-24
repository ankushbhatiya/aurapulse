import asyncio
import json
import os
import uuid
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Security, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis
from api.config import settings
from engine.celery_app import run_single_swarm, celery_app
from engine.report_agent import ReportAgent
from graph.constructor import GraphConstructor
from api.logger import logger

app = FastAPI(title="AuraPulse API", version="1.4.0")

# Security Setup
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if settings.API_KEY and api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return api_key

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Async redis client
redis_client = aioredis.from_url(settings.redis_full_url, decode_responses=True)

# --- MODELS ---

class ABPayload(BaseModel):
    postA: str
    postB: str
    agent_count: int = settings.DEFAULT_AGENT_COUNT

class DraftPayload(BaseModel):
    session_id: str
    postA: str
    postB: str
    agent_count: int

class IngestPayload(BaseModel):
    text: str
    client_id: Optional[str] = "development"

# --- ROUTERS ---

v1_router = APIRouter(prefix="/api/v1")

@v1_router.post("/simulate", dependencies=[Depends(get_api_key)])
async def trigger_simulation(payload: ABPayload):
    sim_id = str(uuid.uuid4())[:8]
    
    # Store simulation metadata
    sim_meta = {
        "id": sim_id,
        "timestamp": str(time.time()),
        "postA": payload.postA,
        "postB": payload.postB,
        "agent_count": str(payload.agent_count),
        "status": "Running"
    }
    await redis_client.hset(f"sim:{sim_id}:meta", mapping=sim_meta)
    await redis_client.lpush("simulations:list", sim_id)
    
    # Trigger TWO independent celery tasks
    logger.info(f"Triggering simulation {sim_id} with {payload.agent_count} agents")
    taskA = run_single_swarm.delay("TrackA", payload.postA, sim_id, payload.agent_count)
    taskB = run_single_swarm.delay("TrackB", payload.postB, sim_id, payload.agent_count)
    
    # Store task IDs so we can stop them if requested
    await redis_client.hset(f"sim:{sim_id}:tasks", mapping={
        "TrackA": taskA.id,
        "TrackB": taskB.id
    })
    
    return {"simulation_id": sim_id, "status": "Started"}

@v1_router.post("/stop/{sim_id}", dependencies=[Depends(get_api_key)])
async def stop_simulation(sim_id: str):
    logger.info(f"Stopping simulation {sim_id}")
    tasks = await redis_client.hgetall(f"sim:{sim_id}:tasks")
    for track, task_id in tasks.items():
        celery_app.control.revoke(task_id, terminate=True)
    
    await redis_client.hset(f"sim:{sim_id}:meta", "status", "Stopped")
    return {"status": "Simulation stopped", "id": sim_id}

@v1_router.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": time.time(), "version": "v1"}

@v1_router.get("/simulations")
async def list_simulations():
    sim_ids = await redis_client.lrange("simulations:list", 0, 19) # Last 20
    results = []
    for sid in sim_ids:
        meta = await redis_client.hgetall(f"sim:{sid}:meta")
        if meta:
            results.append(meta)
    return results

@v1_router.get("/history/{sim_id}/{track_id}")
async def get_history(sim_id: str, track_id: str):
    logs = await redis_client.lrange(f"logs:{sim_id}:{track_id}", 0, -1)
    return [json.loads(l) for l in logs]

@v1_router.get("/report/{sim_id}/{track_id}")
async def get_report(sim_id: str, track_id: str, force_refresh: bool = False):
    report_key = f"report:{sim_id}:{track_id}"
    
    # 1. Check if report already exists in Redis (unless force_refresh is true)
    if not force_refresh:
        cached_report = await redis_client.get(report_key)
        if cached_report:
            return json.loads(cached_report)

    # 2. If not, generate it
    logs = await redis_client.lrange(f"logs:{sim_id}:{track_id}", 0, -1)
    if not logs:
        logger.warning(f"No simulation data found for {sim_id}:{track_id}")
        raise HTTPException(status_code=404, detail="No simulation data found.")
    
    simulation_data = [json.loads(l) for l in logs]
    logger.info(f"Generating report for {sim_id}:{track_id} with {len(simulation_data)} entries")
    agent = ReportAgent()
    report = await agent.generate_report(track_id, simulation_data)
    
    # 3. Store the result in Redis so it's persistent
    await redis_client.set(report_key, json.dumps(report))
    
    return report

@v1_router.get("/stream")
async def stream_simulation(sim_id: Optional[str] = None):
    async def event_generator():
        pubsub = redis_client.pubsub()
        channel = f"sim_stream:{sim_id}" if sim_id else "sim_stream"
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {"data": message["data"]}
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return EventSourceResponse(event_generator())

# --- DRAFT ENDPOINTS ---

@v1_router.post("/draft", dependencies=[Depends(get_api_key)])
async def save_draft(payload: DraftPayload):
    draft_key = f"draft:{payload.session_id}"
    draft_data = {
        "postA": payload.postA,
        "postB": payload.postB,
        "agent_count": str(payload.agent_count)
    }
    await redis_client.hset(draft_key, mapping=draft_data)
    return {"status": "Draft saved", "session_id": payload.session_id}

@v1_router.get("/draft/{session_id}")
async def get_draft(session_id: str):
    draft_key = f"draft:{session_id}"
    draft_data = await redis_client.hgetall(draft_key)
    if not draft_data:
        return {"postA": "", "postB": "", "agent_count": settings.DEFAULT_AGENT_COUNT}
    
    return {
        "postA": draft_data.get("postA", ""),
        "postB": draft_data.get("postB", ""),
        "agent_count": int(draft_data.get("agent_count", str(settings.DEFAULT_AGENT_COUNT)))
    }

@v1_router.delete("/draft/{session_id}", dependencies=[Depends(get_api_key)])
async def delete_draft(session_id: str):
    draft_key = f"draft:{session_id}"
    await redis_client.delete(draft_key)
    return {"status": "Draft deleted", "session_id": session_id}

# --- KNOWLEDGE INGESTION ---

@v1_router.post("/ingest", dependencies=[Depends(get_api_key)])
async def ingest_knowledge(payload: IngestPayload):
    try:
        constructor = GraphConstructor()
        tenant = payload.client_id or os.getenv("APP_ENV", "development")
        constructor.process_seed_text(payload.text, client_id=tenant)
        constructor.close()
        return {"status": "Ingestion complete", "tenant": tenant}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the app
app.include_router(v1_router)

# Root redirect or simple message
@app.get("/")
async def root():
    return {"message": "AuraPulse API is running. Use /api/v1 for endpoints.", "docs": "/docs"}
