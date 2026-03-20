from engine.llm import generate_response
import os
import time
import asyncio
from litellm import completion, acompletion
from litellm.exceptions import RateLimitError
from dotenv import load_dotenv

# Optional Zep Integration
try:
    from zep_python import ZepClient
    from zep_python.models import Message
except ImportError:
    ZepClient = None

load_dotenv(".env.development")

# LLM Config
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

# Zep Config
ZEP_API_KEY = os.getenv("ZEP_API_KEY")
ZEP_API_URL = os.getenv("ZEP_API_URL", "https://api.zep.cloud")

zep_client = None
if ZEP_API_KEY and ZepClient:
    zep_client = ZepClient(api_url=ZEP_API_URL, api_key=ZEP_API_KEY)

async def get_agent_memory(session_id: str) -> str:
    """Fetches long-term memory for an agent from Zep Cloud."""
    if not zep_client:
        return "None."
    try:
        # Fetch last 5 messages for context
        memory = await zep_client.memory.aget_memory(session_id)
        if memory and memory.messages:
            history = [m.content for m in memory.messages[-5:]]
            return " | ".join(history)
    except Exception as e:
        print(f"Zep Memory Fetch Error: {e}")
    return "None."

async def add_agent_memory(session_id: str, content: str):
    """Saves a new agent reaction to Zep Cloud."""
    if not zep_client:
        return
    try:
        message = Message(role="assistant", content=content)
        await zep_client.memory.aadd_memory(session_id, [message])
    except Exception as e:
        print(f"Zep Memory Save Error: {e}")

async def generate_agent_response_async(persona: dict, post_text: str, graph_context: str, sim_id: str = "global") -> str:
    # 1. Fetch Long-Term Memory
    long_term_memory = await get_agent_memory(persona["id"])

    # ... prompt construction ...
    
    comment = "Error: Agent silent."
    # Check circuit breaker before starting
    from engine.llm import generate_response, is_circuit_broken
    if is_circuit_broken(sim_id):
        return "CIRCUIT_BREAKER_TRIPPED"

    for attempt in range(3):
        try:
            # We use our engine.llm.generate_response wrapper logic here too
            # or just import the token counting logic. 
            # For simplicity, let's call our existing generate_response logic but async
            # But generate_response is sync. Let's make it consistent.
            
            # To avoid refactoring too much, I'll just import the counter here
            from engine.llm import r
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            tokens = token_counter(model="gpt-4o-mini", messages=messages)
            r.incrby(f"tokens:{sim_id}", tokens)

            completion_args = {
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500
            }
            if LLM_BASE_URL:
                completion_args["api_base"] = LLM_BASE_URL

            response = await acompletion(**completion_args)
            content = response.choices[0].message.content.strip()
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            comment = lines[-1] if len(lines) > 1 else content
            
            # 2. Save new reaction to Memory
            await add_agent_memory(persona["id"], comment)
            break
        except RateLimitError:
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            print(f"LLM Error: {e}")
            break
            
    return comment

def generate_agent_response(persona: dict, post_text: str, graph_context: str, sim_id: str = "global") -> str:
    return asyncio.run(generate_agent_response_async(persona, post_text, graph_context, sim_id))

if __name__ == "__main__":
    test_persona = {"id": "test_user_1", "name": "Kyle", "demographic": "Gen Z", "bias": "Hater", "vibe": "Aggressive"}
    print(generate_agent_response(test_persona, "I love my new steakhouse!", "Regarding Veganism: Advocates heavily."))
