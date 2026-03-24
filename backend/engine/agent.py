from engine.llm import STRATEGIC_LLM, AGENT_LLM, LLM_BASE_URL, is_circuit_broken, r
import os
import time
import asyncio
from litellm import completion, acompletion, token_counter
from api.config import settings
from api.logger import logger

# Optional Zep Integration
try:
    from zep_cloud import Zep, Message as ZepMessage
except ImportError:
    Zep = None
    ZepMessage = None

# Zep Config
ZEP_API_KEY = settings.ZEP_API_KEY

logger.debug(f"ZEP_API_KEY starts with: {str(ZEP_API_KEY)[:10]}...")

zep_client = None
if ZEP_API_KEY and Zep:
    logger.info(f"Initializing Zep Cloud client")
    zep_client = Zep(api_key=ZEP_API_KEY)


async def get_agent_memory(session_id: str) -> str:
    if not zep_client:
        logger.debug(f"Zep client not initialized. Skipping memory fetch for {session_id}")
        return "None."
    try:
        logger.debug(f"Fetching Zep memory for session: {session_id}")
        # Zep Cloud uses thread.get_messages to retrieve messages
        response = zep_client.thread.get(thread_id=session_id, lastn=5)
        if response and response.messages:
            history = [m.content for m in response.messages]
            logger.debug(f"Fetched {len(history)} messages from Zep for {session_id}")
            return " | ".join(history)
    except Exception as e:
        logger.error(f"Zep Memory Fetch Error for {session_id}: {e}")
    return "None."


async def add_agent_memory(session_id: str, user_content: str, assistant_content: str):
    if not zep_client:
        return
    try:
        logger.debug(f"Saving interaction to Zep for session: {session_id}")

        messages = [
            ZepMessage(role="user", content=user_content),
            ZepMessage(role="assistant", content=assistant_content),
        ]

        # Create user first if it doesn't exist (Zep Cloud requires this)
        try:
            zep_client.user.get(user_id=session_id)
        except Exception:
            # User doesn't exist, create it
            try:
                zep_client.user.add(user_id=session_id)
            except Exception:
                pass

        # Create thread first if it doesn't exist (Zep Cloud requires this)
        try:
            zep_client.thread.get(thread_id=session_id)
        except Exception:
            # Thread doesn't exist, create it
            zep_client.thread.create(thread_id=session_id, user_id=session_id)

        zep_client.thread.add_messages(thread_id=session_id, messages=messages)
        logger.debug(f"Successfully saved pair to Zep for {session_id}")
    except Exception as e:
        logger.error(f"Zep Memory Save Error for {session_id}: {e}")


async def generate_agent_response_async(
    persona: dict, post_text: str, graph_context: str, sim_id: str = "global"
) -> str:
    # 1. Fetch Long-Term Memory (Session ID is Persona ID)
    session_id = str(persona["id"])
    long_term_memory = await get_agent_memory(session_id)

    # 2. Build Prompts
    system_prompt = f"""
    You are an AI simulating a real social media user.
    Name: {persona["name"]}
    Demographic: {persona["demographic"]}
    Bias: {persona["bias"]}
    Vibe: {persona["vibe"]}
    Interest: {persona.get("interest", "General")}
    
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
    if await is_circuit_broken(sim_id):
        return "CIRCUIT_BREAKER_TRIPPED"

    comment = "Error: Agent silent."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(3):
        try:
            # Count Tokens (using AGENT_LLM)
            tokens = token_counter(model="gpt-4o-mini", messages=messages)
            await r.incrby(f"tokens:{sim_id}", tokens)

            completion_args = {
                "model": AGENT_LLM,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500,
            }
            if LLM_BASE_URL:
                completion_args["api_base"] = LLM_BASE_URL

            response = await acompletion(**completion_args)
            content = response.choices[0].message.content.strip()
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            comment = lines[-1] if len(lines) > 1 else content

            # 2. Save new interaction to Memory
            await add_agent_memory(session_id, post_text, comment)
            break
        except Exception as e:
            logger.error(f"Agent LLM Error ({persona['name']}): {e}")
            await asyncio.sleep(2**attempt)

    return comment


def generate_agent_response(
    persona: dict, post_text: str, graph_context: str, sim_id: str = "global"
) -> str:
    return asyncio.run(
        generate_agent_response_async(persona, post_text, graph_context, sim_id)
    )


if __name__ == "__main__":
    test_persona = {
        "id": "test_user_1",
        "name": "Kyle",
        "demographic": "Gen Z",
        "bias": "Hater",
        "vibe": "Aggressive",
    }
    logger.info(
        generate_agent_response(
            test_persona,
            "I love my new steakhouse!",
            "Regarding Veganism: Advocates heavily.",
        )
    )
