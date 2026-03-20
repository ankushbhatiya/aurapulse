import os
import json
import uuid
from typing import List, Dict
from neo4j import GraphDatabase
from litellm import completion
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/.aura/aura.cfg")) if os.path.exists(os.path.expanduser("~/.aura/aura.cfg")) else load_dotenv("/app/.aura/aura.cfg")

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/minimax/minimax-m2.5")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1/")

class GraphConstructor:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def chunk_text(self, text: str, chunk_size=500, overlap=50) -> List[str]:
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i : i + chunk_size])
        return chunks

    def extract_entities_and_relationships(self, text_chunk: str) -> Dict:
        prompt = f"""
        ### TASK
        Extract entities and relationships from the text below for a social simulation knowledge graph.
        
        ### TEXT
        "{text_chunk}"
        
        ### ONTOLOGY RULES
        - Entity Types: Person, Organization, Policy, Concept, Event, Brand
        - Relationship Types: SUPPORTS, OPPOSES, BELIEVES, WORKS_FOR, CONTRADICTS
        
        ### OUTPUT FORMAT
        Output valid JSON ONLY. NO preamble. NO reasoning. 
        Format:
        {{
          "nodes": [ {{"name": "...", "type": "..."}} ],
          "edges": [ {{"from": "...", "to": "...", "type": "...", "description": "..."}} ]
        }}
        """
        
        for attempt in range(3):
            try:
                response = completion(
                    model=LLM_MODEL,
                    api_base=LLM_BASE_URL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1000
                )
                content = response.choices[0].message.content.strip()
                
                # Basic cleaning if the model included markers
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # If there is reasoning before JSON, try to find the first '{'
                if not content.startswith("{"):
                    start = content.find("{")
                    if start != -1:
                        content = content[start:]
                
                # Find the last '}'
                end = content.rfind("}")
                if end != -1:
                    content = content[:end+1]

                return json.loads(content)
            except Exception as e:
                print(f"Extraction Attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return {"nodes": [], "edges": []}
        return {"nodes": [], "edges": []}

    def ingest_into_neo4j(self, data: Dict, client_id="CLIENT_A"):
        with self.driver.session() as session:
            # Ensure Client exists
            session.run("MERGE (c:Celebrity {id: $client_id})", client_id=client_id)
            
            # Create Nodes
            for node in data.get("nodes", []):
                query = f"""
                MERGE (n:{node['type']} {{name: $name}})
                SET n.tenant_id = $client_id
                """
                try:
                    session.run(query, name=node['name'], client_id=client_id)
                except Exception as e:
                    print(f"Failed to ingest node {node}: {e}")
            
            # Create Edges
            for edge in data.get("edges", []):
                # Using general labels for match to ensure compatibility with merging nodes above
                query = f"""
                MATCH (a {{name: $from}}), (b {{name: $to}})
                WHERE a.tenant_id = $client_id AND b.tenant_id = $client_id
                MERGE (a)-[r:{edge['type']}]->(b)
                SET r.description = $description
                """
                try:
                    session.run(query, **edge, client_id=client_id)
                except Exception as e:
                    print(f"Failed to ingest edge {edge}: {e}")

    def process_seed_text(self, text: str, client_id="CLIENT_A"):
        chunks = self.chunk_text(text)
        print(f"Processing {len(chunks)} chunks...")
        for i, chunk in enumerate(chunks):
            print(f"  - Chunk {i+1}/{len(chunks)}...")
            data = self.extract_entities_and_relationships(chunk)
            print(f"    - Extracted {len(data.get('nodes', []))} nodes, {len(data.get('edges', []))} edges.")
            self.ingest_into_neo4j(data, client_id)
        print("Graph Construction Complete.")

if __name__ == "__main__":
    constructor = GraphConstructor()
    test_text = "Celeb X is a vegan activist who strictly opposes animal cruelty. They are currently partnered with Beyond Meat but are facing backlash for their recent steakhouse visit."
    constructor.process_seed_text(test_text)
    constructor.close()
