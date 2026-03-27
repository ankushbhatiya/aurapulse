import json
import uuid
import random
import os
import asyncio
from typing import List, Dict
from litellm import completion, acompletion
from api.config import settings
from api.logger import logger
from graph.neo4j_utils import neo4j_connector
from api.redis_utils import redis_manager

async def get_grounding_concepts(client_id: str = "CLIENT_A") -> List[str]:
    try:
        driver = neo4j_connector.get_driver()
        with driver.session() as session:
            result = session.run(
                "MATCH (n) WHERE n.tenant_id = $client_id AND NOT n:Celebrity RETURN n.name as name LIMIT 20",
                client_id=client_id
            )
            concepts = [r["name"] for r in result]
        return concepts if concepts else ["General Social Media", "Trending Topics"]
    except Exception as e:
        logger.error(f"Failed to fetch grounding concepts: {e}")
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
            "temperature": 0.85,
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
        logger.error(f"LLM Persona Generation Error: {e}. Falling back to random.")
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
    concepts = await get_grounding_concepts(client_id)
    logger.info(f"Generating {count} high-fidelity personas using {settings.STRATEGIC_LLM_MODEL} in parallel...")
    
    semaphore = asyncio.Semaphore(4)

    async def sem_create(i):
        async with semaphore:
            return await create_persona_llm(concepts, unique_id=i)

    tasks = [sem_create(i) for i in range(count)]
    raw_personas = await asyncio.gather(*tasks)
    
    unique_personas = []
    seen_names = set()
    for p in raw_personas:
        if p["name"] not in seen_names:
            unique_personas.append(p)
            seen_names.add(p["name"])
        else:
            p["name"] = f"{p['name']} ({uuid.uuid4().hex[:4]})"
            unique_personas.append(p)

    # Save to Redis
    redis_client = redis_manager.get_client()
    key = f"personas:{client_id}"
    # Clear existing and add new
    await redis_client.delete(key)
    if unique_personas:
        # Use SADD for uniqueness and efficiency if we just need the set
        # But we need the full objects, so we'll use a Hash or keep as a list for now
        # Actually, for random sample, a list is fine, but let's store them as individual items in a list or set
        await redis_client.set(key, json.dumps(unique_personas))
        
    # Also save to file
    file_path = settings.PERSONAS_FILE
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(unique_personas, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save personas to file: {e}")
        
    logger.info(f"Ingestion complete. {len(unique_personas)} personas saved to Redis key '{key}'")

async def load_personas_from_redis(client_id="CLIENT_A") -> List[Dict]:
    try:
        redis_client = redis_manager.get_client()
        data = await redis_client.get(f"personas:{client_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Error loading personas from Redis: {e}")
    return []

if __name__ == "__main__":
    asyncio.run(generate_grounded_personas(4)) # Generate exactly 4 to test stability
