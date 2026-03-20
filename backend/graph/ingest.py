import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD"))

def ingest_data():
    # Use absolute path or relative to project root
    file_path = os.path.join(os.path.dirname(__file__), "mock_data.json")
    with open(file_path, "r") as f:
        data = json.load(f)

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            # Create Celebrity root node
            session.run("MERGE (c:Celebrity {id: 'CLIENT_A', name: 'Test Celeb'})")
            
            for item in data:
                query = """
                MATCH (c:Celebrity {id: 'CLIENT_A'})
                MERGE (con:Concept {name: $concept})
                MERGE (c)-[r:BELIEVES]->(con)
                SET r.stance = $stance
                """
                session.run(query, concept=item["concept"], stance=item["stance"])
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_data()
