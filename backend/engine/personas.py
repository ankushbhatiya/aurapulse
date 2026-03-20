import json
import uuid
import random
import os
import asyncio
from typing import List, Dict
from neo4j import GraphDatabase
from litellm import completion, acompletion
from engine.llm import STRATEGIC_LLM, LLM_BASE_URL
from dotenv import load_dotenv

# Load global config first
CONFIG_PATH = os.path.expanduser("~/.aura/aura.cfg")
load_dotenv(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else load_dotenv("/app/.aura/aura.cfg")

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def get_grounding_concepts(client_id="CLIENT_A") -> List[str]:
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run(
                "MATCH (n) WHERE n.tenant_id = $client_id AND NOT n:Celebrity RETURN n.name as name LIMIT 20",
                client_id=client_id
            )
            concepts = [r["name"] for r in result]
        driver.close()
        return concepts if concepts else ["General Social Media", "Trending Topics"]
    except Exception:
        return ["General Social Media", "Trending Topics"]

async def create_persona_llm(concepts: List[str]) -> Dict:
    """Uses Strategic LLM to generate a high-fidelity persona with strict JSON enforcement."""
    system_prompt = """
    You are a specialized Persona Generator. 
    CRITICAL: You MUST output valid JSON ONLY. 
    DO NOT include any thoughts, reasoning, or preamble. 
    If you include any text other than the JSON object, the system will fail.
    """
    
    user_prompt = f"""
    Generate a unique social media user persona interested in: {', '.join(concepts)}.
    
    Output this EXACT JSON structure:
    {{
      "name": "Creative name",
      "demographic": "One of: Gen Z, Millennial, Gen X, Boomer",
      "bias": "One of: Super-fan, Hater, Casual Observer, Activist, Investor, Skeptic, Troll",
      "vibe": "One of: Supportive, Critical, Funny, Aggressive, Neutral, Thoughtful, Sarcastic, Hyper",
      "interest": "One from the list provided",
      "description": "1-sentence backstory."
    }}
    """
    
    try:
        completion_args = {
            "model": STRATEGIC_LLM,
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
        
        # Robust JSON cleaning
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        if not content.startswith("{"):
            start = content.find("{")
            if start != -1:
                content = content[start:]
        
        end = content.rfind("}")
        if end != -1:
            content = content[:end+1]
            
        data = json.loads(content)
        data["id"] = str(uuid.uuid4())
        return data
    except Exception as e:
        print(f"LLM Persona Generation Error: {e}. Falling back to random.")
        # Fallback to random if LLM fails
        return {
            "id": str(uuid.uuid4()),
            "name": f"User_{random.randint(1000, 9999)}",
            "bias": "Casual Observer",
            "demographic": "Millennial",
            "vibe": "Neutral",
            "interest": random.choice(concepts),
            "description": "A fallback user created due to system load."
        }

async def generate_grounded_personas(count=100, client_id="CLIENT_A"):
    concepts = get_grounding_concepts(client_id)
    print(f"Generating {count} high-fidelity personas using {STRATEGIC_LLM} in parallel (limit=4)...")
    
    semaphore = asyncio.Semaphore(4)

    async def sem_create():
        async with semaphore:
            return await create_persona_llm(concepts)

    tasks = [sem_create() for _ in range(count)]
    personas = await asyncio.gather(*tasks)
    
    file_path = os.path.expanduser("~/.aura/personas.json")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(personas, f, indent=2)
    print(f"Ingestion complete. {count} personas saved to {file_path}")

if __name__ == "__main__":
    asyncio.run(generate_grounded_personas(4)) # Generate exactly 4 to test stability
