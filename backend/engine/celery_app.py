import os
import time
import redis
import json
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("aurapulse", broker=REDIS_URL, backend=REDIS_URL)

redis_client = redis.Redis.from_url(REDIS_URL)

@celery_app.task
def mock_simulate(post_text: str):
    for i in range(5):
        time.sleep(1)
        message = {"id": i, "comment": f"Agent {i} reacting to: {post_text}"}
        redis_client.publish('sim_stream', json.dumps(message))
    return "Done"
