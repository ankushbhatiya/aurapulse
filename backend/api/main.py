import asyncio
import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as aioredis
from engine.celery_app import mock_simulate

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PostPayload(BaseModel):
    post: str

@app.post("/simulate")
async def trigger_simulation(payload: PostPayload):
    task = mock_simulate.delay(payload.post)
    return {"task_id": task.id, "status": "Processing"}

@app.get("/stream")
async def stream_simulation():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = aioredis.from_url(redis_url)
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
