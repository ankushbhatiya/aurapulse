from engine.llm import STRATEGIC_LLM, AGENT_LLM, LLM_BASE_URL, is_circuit_broken, r
import os
import time
import asyncio
from litellm import completion, acompletion, token_counter
from dotenv import load_dotenv

# Load global config
CONFIG_PATH = "/Users/ankush/.aura/aura.cfg"
load_dotenv(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else load_dotenv("/app/.aura/aura.cfg")

# Optional Zep Integration
try:
    from zep_python import ZepClient
    from zep_python.models import Message
except ImportError:
    ZepClient = None

# Zep Config
ZEP_API_KEY = os.getenv("ZEP_API_KEY")
ZEP_API_URL = os.getenv("ZEP_API_URL", "https://api.zep.cloud")

zep_client = None
if ZEP_API_KEY and ZepClient:
    zep_client = ZepClient(api_url=ZEP_API_URL, api_key=ZEP_API_KEY)

async def get_agent_memory(session_id: str) -> str:
    if not zep_client: return "None."
    try:
        memory = await zep_client.memory.aget_memory(session_id)
        if memory and memory.messages:
            history = [m.content for m in memory.messages[-5:]]
            return " | ".join(history)
    except Exception: pass
    return "None."

async def add_agent_memory(session_id: str, content: str):
    if not zep_client: return
    try:
        message = Message(role="assistant", content=content)
        await zep_client.memory.aadd_memory(session_id, [message])
    except Exception: pass

async def generate_agent_response_async(persona: dict, post_text: str, graph_context: str, sim_id: str = "global") -> str:
    # 1. Fetch Long-Term Memory
    long_term_memory = await get_agent_memory(persona["id"])

    # 2. Build Prompts
    system_prompt = f"""
    You are an AI simulating a real social media user.
    Name: {persona['name']}
    Demographic: {persona['demographic']}
    Bias: {persona['bias']}
    Vibe: {persona['vibe']}
    Interest: {persona.get('interest', 'General')}
    
    ### LONG-TERM MEMORY (Your past actions)
    "{long_term_memory}"

    ### INSTRUCTIONS:
    - Write a short, realistic 1-sentence comment. 
    - Use lowercase or slang if it fits the Gen Z profile. 
    - Be aggressive if you are a hater. Be protective if you are a super-fan.
    - Limit: 15 words.
    - DO NOT use hashtags or quotes.
    - CRITICAL: ONLY output the comment text. DO NOT include any reasoning, thoughts, or metadata.
    """
    
    user_prompt = f"""
    POST: "{post_text}"
    CONTEXT: "{graph_context}"
    """
    
    # 3. Check circuit breaker
    if is_circuit_broken(sim_id):
        return "CIRCUIT_BREAKER_TRIPPED"

    comment = "Error: Agent silent."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    for attempt in range(3):
        try:
            # Count Tokens (using AGENT_LLM)
            tokens = token_counter(model="gpt-4o-mini", messages=messages)
            r.incrby(f"tokens:{sim_id}", tokens)

            completion_args = {
                "model": AGENT_LLM,
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
            
            await add_agent_memory(persona["id"], comment)
            break
        except Exception as e:
            print(f"Agent LLM Error ({persona['name']}): {e}")
            await asyncio.sleep(2 ** attempt)
            
    return comment

def generate_agent_response(persona: dict, post_text: str, graph_context: str, sim_id: str = "global") -> str:
    return asyncio.run(generate_agent_response_async(persona, post_text, graph_context, sim_id))
