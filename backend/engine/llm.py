import os
import time
import redis
from litellm import completion, token_counter
from litellm.exceptions import RateLimitError
from api.config import settings

# Redis for Circuit Breaker
r = redis.Redis.from_url(settings.redis_full_url)

# Dual LLM Config
STRATEGIC_LLM = settings.STRATEGIC_LLM_MODEL
AGENT_LLM = settings.AGENT_LLM_MODEL
LLM_BASE_URL = settings.LLM_BASE_URL

def is_circuit_broken(sim_id: str) -> bool:
    # Disable circuit breaker for local testing
    base_url = settings.LLM_BASE_URL or ""
    is_local = "localhost" in base_url or "host.docker.internal" in base_url or not base_url
    
    limit = 1000000 
    usage = int(r.get(f"tokens:{sim_id}") or 0)
    
    if usage > limit and not is_local:
        print(f"!!! CIRCUIT BREAKER TRIPPED !!! Sim: {sim_id} | Usage: {usage} | Limit: {limit} | BaseURL: {base_url} | LocalBypass: {is_local}")
        return True
    
    if usage > limit and is_local:
        # Just a warning for local, don't actually break
        print(f"--- CIRCUIT BREAKER WARNING (BYPASSED) --- Sim: {sim_id} | Usage: {usage} | BaseURL: {base_url}")
        return False

    return False

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
