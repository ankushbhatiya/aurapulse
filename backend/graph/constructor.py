import os
import json
import uuid
from typing import List, Dict
from neo4j import GraphDatabase
from litellm import completion
from api.config import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter

class GraphConstructor:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI, 
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD) if settings.NEO4J_PASSWORD else None
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", ".", " ", ""]
        )

    def close(self):
        self.driver.close()

    def chunk_text(self, text: str) -> List[str]:
        return self.splitter.split_text(text)

    def extract_entities_and_relationships(self, text_chunk: str) -> Dict:
        prompt = f"""
        ### TASK
        You are a Knowledge Graph Expert. Extract entities and relationships from the text below to build a social simulation model.
        
        ### TEXT
        "{text_chunk}"
        
        ### ONTOLOGY RULES
        - **Entity Types**: 
          - Person: Individuals (e.g., "John Doe", "The CEO")
          - Organization: Groups, Companies, Agencies (e.g., "Beyond Meat", "The UN")
          - Policy: Rules, Guidelines, Legislation (e.g., "Vegan Guidelines", "GDPR")
          - Concept: Abstract ideas, movements, topics (e.g., "Veganism", "Sustainability", "Backlash")
          - Event: Specific occurrences (e.g., "Steakhouse visit", "Product Launch")
          - Brand: Commercial identities (e.g., "AuraPulse", "Nike")
        
        - **Relationship Types**: 
          - SUPPORTS: Entity A favors/advocates for Entity B
          - OPPOSES: Entity A is against/protests Entity B
          - BELIEVES: Entity A holds a specific stance on Concept B
          - WORKS_FOR: Person A is employed by Organization B
          - CONTRADICTS: Entity A's actions go against Policy/Concept B
          - ASSOCIATED_WITH: General link between entities
        
        ### OUTPUT FORMAT
        Output valid JSON ONLY. NO preamble. NO reasoning. 
        
        Example:
        {{
          "nodes": [ {{"name": "Celeb X", "type": "Person"}}, {{"name": "Veganism", "type": "Concept"}} ],
          "edges": [ {{"from": "Celeb X", "to": "Veganism", "type": "SUPPORTS", "description": "Is a vegan activist"}} ]
        }}
        """
        
        for attempt in range(3):
            try:
                response = completion(
                    model=settings.STRATEGIC_LLM_MODEL,
                    api_base=settings.LLM_BASE_URL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2000
                )
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

                return json.loads(content)
            except Exception as e:
                print(f"Extraction Attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return {"nodes": [], "edges": []}
        return {"nodes": [], "edges": []}

    def ingest_into_neo4j(self, data: Dict, client_id="CLIENT_A"):
        with self.driver.session() as session:
            # Ensure Client exists (using Celebrity as a proxy for the 'Owner' of the graph context)
            session.run("MERGE (c:Celebrity {name: $client_id}) SET c.tenant_id = $client_id", client_id=client_id)
            
            # Create Nodes
            for node in data.get("nodes", []):
                # Sanitize label
                label = node['type'].replace(" ", "_")
                query = f"""
                MERGE (n:{label} {{name: $name, tenant_id: $client_id}})
                """
                try:
                    session.run(query, name=node['name'], client_id=client_id)
                except Exception as e:
                    print(f"Failed to ingest node {node}: {e}")
            
            # Create Edges
            for edge in data.get("edges", []):
                # Using general labels for match but ensuring tenant isolation
                rel_type = edge['type'].replace(" ", "_")
                query = f"""
                MATCH (a {{name: $from, tenant_id: $client_id}}), (b {{name: $to, tenant_id: $client_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.description = $description
                """
                try:
                    session.run(query, **edge, client_id=client_id)
                except Exception as e:
                    print(f"Failed to ingest edge {edge}: {e}")

    def process_seed_text(self, text: str, client_id="CLIENT_A"):
        chunks = self.chunk_text(text)
        print(f"Processing {len(chunks)} chunks with Recursive Splitter...")
        for i, chunk in enumerate(chunks):
            print(f"  - Chunk {i+1}/{len(chunks)} (len: {len(chunk)})...")
            data = self.extract_entities_and_relationships(chunk)
            print(f"    - Extracted {len(data.get('nodes', []))} nodes, {len(data.get('edges', []))} edges.")
            self.ingest_into_neo4j(data, client_id)
        print("Graph Construction Complete.")

if __name__ == "__main__":
    constructor = GraphConstructor()
    test_text = "Celeb X is a vegan activist who strictly opposes animal cruelty. They are currently partnered with Beyond Meat but are facing backlash for their recent steakhouse visit."
    constructor.process_seed_text(test_text)
    constructor.close()
