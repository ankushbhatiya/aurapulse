from engine.llm import generate_response
import os
import time
from litellm import completion
from litellm.exceptions import RateLimitError
from dotenv import load_dotenv

load_dotenv()

# Use local LLM if base_url is provided
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

def generate_agent_response(persona: dict, post_text: str, graph_context: str) -> str:
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
            
            # If the model still outputs reasoning, we'll try to get the last line if it's not empty
            # Many reasoning models end with the final answer.
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            if len(lines) > 1:
                # If there are many lines, the last one might be the actual comment
                return lines[-1]
            return content
        except RateLimitError:
            time.sleep(2 ** attempt)
        except Exception as e:
            print(f"LLM Error: {e}")
            break
    return "Error: Agent silent."

if __name__ == "__main__":
    test_persona = {"name": "Kyle", "demographic": "Gen Z", "bias": "Hater", "vibe": "Aggressive"}
    print(generate_agent_response(test_persona, "I love my new steakhouse!", "Regarding Veganism: Advocates heavily, partnered with Beyond Meat."))
