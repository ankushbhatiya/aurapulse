import os
import time
import redis
from litellm import completion, token_counter
from litellm.exceptions import RateLimitError
from dotenv import load_dotenv

# Load global config first
CONFIG_PATH = "/Users/ankush/.aura/aura.cfg"
load_dotenv(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else load_dotenv("/app/.aura/aura.cfg")

# Redis for Circuit Breaker
REDIS_URL_BASE = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_URL = f"{REDIS_URL_BASE}/{REDIS_DB}"
r = redis.Redis.from_url(REDIS_URL)

# Dual LLM Config Defaults
STRATEGIC_LLM = os.getenv("STRATEGIC_LLM_MODEL", "gpt-4o-mini")
AGENT_LLM = os.getenv("AGENT_LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

def is_circuit_broken(sim_id: str) -> bool:
    limit = 10000 
    usage = int(r.get(f"tokens:{sim_id}") or 0)
    return usage > limit

def generate_response(prompt: str, model: str, sim_id: str = "global") -> str:
    """Generic wrapper for LLM calls with token counting and circuit breaking."""
    if is_circuit_broken(sim_id):
        return "CIRCUIT_BREAKER_TRIPPED"

    for attempt in range(3):
        try:
            messages = [{"role": "user", "content": prompt}]
            # Count tokens using a generic model name if needed
            tokens = token_counter(model="gpt-4o-mini", messages=messages)
            r.incrby(f"tokens:{sim_id}", tokens)

            completion_args = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000 if "minimax" in model else 500
            }
            if LLM_BASE_URL:
                completion_args["api_base"] = LLM_BASE_URL

            response = completion(**completion_args)
            return response.choices[0].message.content.strip()
        except RateLimitError:
            time.sleep(2 ** attempt)
        except Exception as e:
            print(f"LLM Error ({model}): {e}")
            break
    return "Error: LLM silent."
