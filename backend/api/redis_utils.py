import asyncio
import redis.asyncio as aioredis
from api.config import settings
from api.logger import logger

class RedisClient:
    _instance = None
    _client = None
    _loop_id = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
        return cls._instance

    def get_client(self):
        try:
            loop = asyncio.get_running_loop()
            current_loop_id = id(loop)
        except RuntimeError:
            current_loop_id = None

        if self._client is None or (current_loop_id and self._loop_id != current_loop_id):
            try:
                self._client = aioredis.from_url(
                    settings.redis_full_url,
                    decode_responses=True
                )
                self._loop_id = current_loop_id
                logger.info(f"Redis client initialized (loop_id={current_loop_id}).")
            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {e}")
                raise
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Redis client closed.")

redis_manager = RedisClient()
