import asyncio
import json
import os
import uuid
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis
import redis
from engine.celery_app import run_dual_swarm, celery_app
from engine.report_agent import ReportAgent
from dotenv import load_dotenv

load_dotenv(".env.development")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard redis client
REDIS_URL_BASE = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_URL = f"{REDIS_URL_BASE}/{REDIS_DB}"
r_std = redis.Redis.from_url(REDIS_URL)

class ABPayload(BaseModel):
    postA: str
    postB: str
    agent_count: int = 20

class DraftPayload(BaseModel):
    session_id: str
    postA: str
    postB: str
    agent_count: int

@app.post("/simulate")
async def trigger_simulation(payload: ABPayload):
    sim_id = str(uuid.uuid4())[:8]
    
    # Store simulation metadata
    sim_meta = {
        "id": sim_id,
        "timestamp": time.time(),
        "postA": payload.postA,
        "postB": payload.postB,
        "agent_count": payload.agent_count,
        "status": "Running"
    }
    r_std.hset(f"sim:{sim_id}:meta", mapping=sim_meta)
    r_std.lpush("simulations:list", sim_id)
    
    # Trigger SINGLE celery task that runs BOTH tracks in parallel
    task = run_dual_swarm.delay(payload.postA, payload.postB, sim_id, payload.agent_count)
    
    # Store task ID so we can stop it if requested
    r_std.hset(f"sim:{sim_id}:tasks", mapping={
        "DualTrack": task.id
    })
    
    return {"simulation_id": sim_id, "status": "Started"}

@app.post("/stop/{sim_id}")
async def stop_simulation(sim_id: str):
    tasks = r_std.hgetall(f"sim:{sim_id}:tasks")
    for track, task_id in tasks.items():
        celery_app.control.revoke(task_id.decode("utf-8"), terminate=True)
    
    r_std.hset(f"sim:{sim_id}:meta", "status", "Stopped")
    return {"status": "Simulation stopped", "id": sim_id}

@app.get("/simulations")
async def list_simulations():
    sim_ids = r_std.lrange("simulations:list", 0, 19) # Last 20
    results = []
    for sid in sim_ids:
        sid_str = sid.decode("utf-8")
        meta = r_std.hgetall(f"sim:{sid_str}:meta")
        if meta:
            # Decode bytes to strings
            results.append({k.decode("utf-8"): v.decode("utf-8") for k, v in meta.items()})
    return results

@app.get("/history/{sim_id}/{track_id}")
async def get_history(sim_id: str, track_id: str):
    logs = r_std.lrange(f"logs:{sim_id}:{track_id}", 0, -1)
    return [json.loads(l.decode("utf-8")) for l in logs]

@app.get("/report/{sim_id}/{track_id}")
async def get_report(sim_id: str, track_id: str, force_refresh: bool = False):
    report_key = f"report:{sim_id}:{track_id}"
    
    # 1. Check if report already exists in Redis (unless force_refresh is true)
    if not force_refresh:
        cached_report = r_std.get(report_key)
        if cached_report:
            return json.loads(cached_report.decode("utf-8"))

    # 2. If not, generate it
    logs = r_std.lrange(f"logs:{sim_id}:{track_id}", 0, -1)
    if not logs:
        raise HTTPException(status_code=404, detail="No simulation data found.")
    
    simulation_data = [json.loads(l.decode("utf-8")) for l in logs]
    agent = ReportAgent()
    report = agent.generate_report(track_id, simulation_data)
    
    # 3. Store the result in Redis so it's persistent
    r_std.set(report_key, json.dumps(report))
    
    return report

@app.get("/stream")
async def stream_simulation():
    r = aioredis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("sim_stream")

    async def event_generator():
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    yield {"data": message["data"].decode("utf-8")}
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe("sim_stream")
            await r.aclose()

    return EventSourceResponse(event_generator())

# --- DRAFT ENDPOINTS ---

@app.post("/draft")
async def save_draft(payload: DraftPayload):
    draft_key = f"draft:{payload.session_id}"
    draft_data = {
        "postA": payload.postA,
        "postB": payload.postB,
        "agent_count": payload.agent_count
    }
    r_std.hset(draft_key, mapping=draft_data)
    return {"status": "Draft saved", "session_id": payload.session_id}

@app.get("/draft/{session_id}")
async def get_draft(session_id: str):
    draft_key = f"draft:{session_id}"
    draft_data = r_std.hgetall(draft_key)
    if not draft_data:
        return {"postA": "", "postB": "", "agent_count": 20}
    
    return {
        "postA": draft_data.get(b"postA", b"").decode("utf-8"),
        "postB": draft_data.get(b"postB", b"").decode("utf-8"),
        "agent_count": int(draft_data.get(b"agent_count", b"20").decode("utf-8"))
    }

@app.delete("/draft/{session_id}")
async def delete_draft(session_id: str):
    draft_key = f"draft:{session_id}"
    r_std.delete(draft_key)
    return {"status": "Draft deleted", "session_id": session_id}
