import os
import time
from litellm import completion
from litellm.exceptions import RateLimitError
from dotenv import load_dotenv

load_dotenv(".env.development")

# Use local LLM if base_url is provided
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

def generate_response(prompt: str, model=LLM_MODEL) -> str:
    for attempt in range(3):
        try:
            # Prepare arguments for completion
            completion_args = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500 # Increased to allow for reasoning but we will try to trim
            }
            
            # Add base_url for local LLM if available
            if LLM_BASE_URL:
                completion_args["api_base"] = LLM_BASE_URL

            response = completion(**completion_args)
            content = response.choices[0].message.content.strip()
            
            # Try to extract the final part if there's reasoning
            # If the model uses <thought> tags, we can trim them.
            # For now, let's just return it and see what happens with a stronger prompt.
            return content
        except RateLimitError:
            wait = 2 ** attempt
            print(f"Rate limit hit. Waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"LLM Error: {e}")
            break
    return "Error: Agent silent."
