from engine.llm import generate_response
import os
import time
import asyncio
from litellm import completion, acompletion
from litellm.exceptions import RateLimitError
from dotenv import load_dotenv

load_dotenv(".env.development")

# Use local LLM if base_url is provided
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

def generate_agent_response(persona: dict, post_text: str, graph_context: str) -> str:
    # ... (existing sync code remains for compatibility)
    system_prompt = f"""
    You are an AI simulating a real social media user.
    Name: {persona['name']}
    Demographic: {persona['demographic']}
    Bias: {persona['bias']}
    Vibe: {persona['vibe']}
    
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
    
    for attempt in range(3):
        try:
            completion_args = {
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            if LLM_BASE_URL:
                completion_args["api_base"] = LLM_BASE_URL

            response = completion(**completion_args)
            content = response.choices[0].message.content.strip()
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            return lines[-1] if len(lines) > 1 else content
        except RateLimitError:
            time.sleep(2 ** attempt)
        except Exception as e:
            print(f"LLM Error: {e}")
            break
    return "Error: Agent silent."

async def generate_agent_response_async(persona: dict, post_text: str, graph_context: str) -> str:
    system_prompt = f"""
    You are an AI simulating a real social media user.
    Name: {persona['name']}
    Demographic: {persona['demographic']}
    Bias: {persona['bias']}
    Vibe: {persona['vibe']}
    
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
    
    for attempt in range(3):
        try:
            completion_args = {
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            if LLM_BASE_URL:
                completion_args["api_base"] = LLM_BASE_URL

            response = await acompletion(**completion_args)
            content = response.choices[0].message.content.strip()
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            return lines[-1] if len(lines) > 1 else content
        except RateLimitError:
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            print(f"LLM Error: {e}")
            break
    return "Error: Agent silent."
