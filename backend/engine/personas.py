import json
import uuid
import random
import os
from typing import List, Dict
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(".env.development")

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def generate_grounded_personas(count=20, client_id="CLIENT_A"):
    """
    Generates personas that are grounded in the entities and relationships 
    found in the Neo4j knowledge graph.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # 1. Fetch concepts/entities to ground the personas
    with driver.session() as session:
        result = session.run(
            "MATCH (n) WHERE n.tenant_id = $client_id AND NOT n:Celebrity RETURN n.name as name, labels(n)[0] as type LIMIT 10",
            client_id=client_id
        )
        concepts = [r["name"] for r in result]
    
    driver.close()
    
    if not concepts:
        concepts = ["General Social Media", "Trending Topics"]

    biases = ["Super-fan", "Hater", "Casual Observer", "Activist", "Investor", "Skeptic"]
    demographics = ["Gen Z", "Millennial", "Gen X", "Boomer"]
    vibes = ["Supportive", "Critical", "Funny", "Aggressive", "Neutral", "Thoughtful"]
    
    personas = []
    for i in range(count):
        # Each persona is obsessed or focused on one concept from the graph
        grounding_concept = random.choice(concepts)
        
        personas.append({
            "id": str(uuid.uuid4()),
            "name": f"User_{i+1000}",
            "bias": random.choice(biases),
            "demographic": random.choice(demographics),
            "vibe": random.choice(vibes),
            "interest": grounding_concept,
            "description": f"A {random.choice(demographics)} {random.choice(biases)} who is particularly vocal about {grounding_concept}."
        })
    
    file_path = os.path.join(os.path.dirname(__file__), "grounded_personas.json")
    with open(file_path, "w") as f:
        json.dump(personas, f, indent=2)
    
    # Also overwrite the default personas.json for the engine to use
    with open(os.path.join(os.path.dirname(__file__), "personas.json"), "w") as f:
        json.dump(personas, f, indent=2)
        
    print(f"Generated {count} grounded personas in {file_path}")

if __name__ == "__main__":
    generate_grounded_personas()
