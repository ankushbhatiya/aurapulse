import asyncio
import json
import os
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis
import redis
from engine.celery_app import run_swarm
from engine.report_agent import ReportAgent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard redis client for non-async parts
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r_std = redis.Redis.from_url(REDIS_URL)

class ABPayload(BaseModel):
    postA: str
    postB: str

@app.post("/simulate")
async def trigger_simulation(payload: ABPayload):
    # Clear previous logs from redis
    r_std.delete("logs:TrackA")
    r_std.delete("logs:TrackB")
    
    # Trigger two independent celery tasks for A/B testing
    run_swarm.delay("TrackA", payload.postA)
    run_swarm.delay("TrackB", payload.postB)
    return {"status": "A/B Simulation Started"}

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
                    data_str = message["data"].decode("utf-8")
                    data = json.loads(data_str)
                    
                    # Also log to a list for the ReportAgent to read later
                    track_id = data.get("track_id")
                    if track_id:
                        r_std.rpush(f"logs:{track_id}", data_str)
                        
                    yield {"data": data_str}
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe("sim_stream")
            await r.aclose()

    return EventSourceResponse(event_generator())

@app.get("/report/{track_id}")
async def get_report(track_id: str):
    # Fetch logs from redis
    logs = r_std.lrange(f"logs:{track_id}", 0, -1)
    if not logs:
        raise HTTPException(status_code=404, detail="No simulation data found for this track.")
    
    simulation_data = [json.loads(l.decode("utf-8")) for l in logs]
    
    agent = ReportAgent()
    report = agent.generate_report(track_id, simulation_data)
    return report
