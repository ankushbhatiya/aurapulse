import os
import json
import uuid
from typing import List, Dict
from litellm import completion
from api.config import settings
from api.logger import logger
from graph.neo4j_utils import neo4j_connector
from langchain_text_splitters import RecursiveCharacterTextSplitter

class GraphConstructor:
    def __init__(self):
        self.driver = neo4j_connector.get_driver()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", ".", " ", ""]
        )

    def close(self):
        # The singleton driver is closed when the app shuts down
        pass

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
        """
        
        for attempt in range(3):
            try:
                completion_args = {
                    "model": settings.STRATEGIC_LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2000
                }
                if settings.LLM_BASE_URL:
                    completion_args["api_base"] = settings.LLM_BASE_URL

                response = completion(**completion_args)
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
                logger.warning(f"Extraction Attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return {"nodes": [], "edges": []}
        return {"nodes": [], "edges": []}

    def ingest_into_neo4j(self, data: Dict, client_id="CLIENT_A"):
        try:
            with self.driver.session() as session:
                # Ensure Client exists
                session.run("MERGE (c:Celebrity {id: $client_id}) SET c.name = $client_id, c.tenant_id = $client_id", client_id=client_id)
                
                # Create Nodes
                for node in data.get("nodes", []):
                    # Sanitize label (basic)
                    label = node.get('type', 'Concept').replace(" ", "_")
                    query = f"MERGE (n:{label} {{name: $name, tenant_id: $client_id}})"
                    session.run(query, name=node['name'], client_id=client_id)
                
                # Create Edges
                for edge in data.get("edges", []):
                    rel_type = edge.get('type', 'ASSOCIATED_WITH').replace(" ", "_")
                    query = f"""
                    MATCH (a {{name: $from, tenant_id: $client_id}}), (b {{name: $to, tenant_id: $client_id}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r.description = $description
                    """
                    session.run(query, **edge, client_id=client_id)
        except Exception as e:
            logger.error(f"Failed to ingest data into Neo4j: {e}")

    def process_seed_text(self, text: str, client_id="CLIENT_A"):
        chunks = self.chunk_text(text)
        logger.info(f"Processing {len(chunks)} chunks for Knowledge Graph construction...")
        for i, chunk in enumerate(chunks):
            data = self.extract_entities_and_relationships(chunk)
            self.ingest_into_neo4j(data, client_id)
        logger.info("Graph Construction Complete.")

if __name__ == "__main__":
    constructor = GraphConstructor()
    test_text = "Celeb X is a vegan activist who strictly opposes animal cruelty."
    constructor.process_seed_text(test_text)
