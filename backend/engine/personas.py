import json
import uuid
import random
import os
import asyncio
from typing import List, Dict
from neo4j import GraphDatabase
from litellm import completion, acompletion
from api.config import settings

def get_grounding_concepts(client_id="CLIENT_A") -> List[str]:
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI, 
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD) if settings.NEO4J_PASSWORD else None
        )
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

async def create_persona_llm(concepts: List[str], unique_id: int = 0) -> Dict:
    """Uses Strategic LLM to generate a high-fidelity persona with strict JSON enforcement."""
    system_prompt = """
    You are a specialized Persona Generator. 
    CRITICAL: You MUST output valid JSON ONLY. 
    DO NOT include any thoughts, reasoning, or preamble. 
    If you include any text other than the JSON object, the system will fail.
    """
    
    user_prompt = f"""
    Generate a unique social media user persona (Reference ID: {unique_id}) interested in: {', '.join(concepts)}.
    
    Output this EXACT JSON structure:
    {{
      "name": "Creative and unique name",
      "demographic": "One of: Gen Z, Millennial, Gen X, Boomer",
      "bias": "One of: Super-fan, Hater, Casual Observer, Activist, Investor, Skeptic, Troll",
      "vibe": "One of: Supportive, Critical, Funny, Aggressive, Neutral, Thoughtful, Sarcastic, Hyper",
      "interest": "One from the list provided",
      "description": "1-sentence backstory."
    }}
    """
    
    try:
        completion_args = {
            "model": settings.STRATEGIC_LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.85, # Increased for more variety
            "max_tokens": 500
        }
        if settings.LLM_BASE_URL:
            completion_args["api_base"] = settings.LLM_BASE_URL

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
    print(f"Generating {count} high-fidelity personas using {settings.STRATEGIC_LLM_MODEL} in parallel (limit=4)...")
    
    semaphore = asyncio.Semaphore(4)

    async def sem_create(i):
        async with semaphore:
            return await create_persona_llm(concepts, unique_id=i)

    tasks = [sem_create(i) for i in range(count)]
    raw_personas = await asyncio.gather(*tasks)
    
    # Ensure name uniqueness
    unique_personas = []
    seen_names = set()
    for p in raw_personas:
        if p["name"] not in seen_names:
            unique_personas.append(p)
            seen_names.add(p["name"])
        else:
            # Append a random string if duplicate name
            p["name"] = f"{p['name']} ({uuid.uuid4().hex[:4]})"
            unique_personas.append(p)

    file_path = settings.PERSONAS_FILE
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(unique_personas, f, indent=2)
    print(f"Ingestion complete. {len(unique_personas)} personas saved to {file_path}")

if __name__ == "__main__":
    asyncio.run(generate_grounded_personas(4)) # Generate exactly 4 to test stability
