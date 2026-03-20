import os
import time
import redis
from litellm import completion, token_counter
from litellm.exceptions import RateLimitError
from dotenv import load_dotenv

load_dotenv(".env.development")

# Redis for Circuit Breaker
REDIS_URL_BASE = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_URL = f"{REDIS_URL_BASE}/{REDIS_DB}"
r = redis.Redis.from_url(REDIS_URL)

# LLM Config
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

def is_circuit_broken(sim_id: str) -> bool:
    """Checks if the token limit for a simulation has been exceeded."""
    limit = 10000 # 10k token limit per sim
    usage = int(r.get(f"tokens:{sim_id}") or 0)
    return usage > limit

def generate_response(prompt: str, sim_id: str = "global") -> str:
    # 1. Check Circuit Breaker
    if is_circuit_broken(sim_id):
        return "CIRCUIT_BREAKER_TRIPPED"

    for attempt in range(3):
        try:
            # 2. Count Tokens
            messages = [{"role": "user", "content": prompt}]
            # Fallback to gpt-4o-mini for counting if local model name not recognized
            model_for_counting = "gpt-4o-mini"
            tokens = token_counter(model=model_for_counting, messages=messages)
            r.incrby(f"tokens:{sim_id}", tokens)

            # 3. Call LLM
            completion_args = {
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500
            }
            if LLM_BASE_URL:
                completion_args["api_base"] = LLM_BASE_URL

            response = completion(**completion_args)
            return response.choices[0].message.content.strip()
        except RateLimitError:
            wait = 2 ** attempt
            time.sleep(wait)
        except Exception as e:
            print(f"LLM Error: {e}")
            break
    return "Error: Agent silent."
