import json
import os
from api.config import settings
from api.logger import logger
from graph.neo4j_utils import neo4j_connector

def ingest_data(client_id: str = "CLIENT_A"):
    # Use absolute path or relative to project root
    file_path = os.path.join(os.path.dirname(__file__), "mock_data.json")
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read mock data: {e}")
        return

    driver = neo4j_connector.get_driver()
    try:
        with driver.session() as session:
            # Create Celebrity root node
            session.run("MERGE (c:Celebrity {id: $client_id, name: 'Test Celeb'})", client_id=client_id)
            
            for item in data:
                query = """
                MATCH (c:Celebrity {id: $client_id})
                MERGE (con:Concept {name: $concept})
                SET con.tenant_id = $client_id
                MERGE (c)-[r:BELIEVES]->(con)
                SET r.stance = $stance
                """
                session.run(query, client_id=client_id, concept=item["concept"], stance=item["stance"])
        logger.info(f"Ingestion complete for tenant: {client_id}")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")

if __name__ == "__main__":
    ingest_data()
