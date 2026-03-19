import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))

def setup_constraints():
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            print("Creating constraints...")
            session.run("CREATE CONSTRAINT FOR (c:Celebrity) REQUIRE c.id IS UNIQUE")
            session.run("CREATE CONSTRAINT FOR (con:Concept) REQUIRE con.name IS UNIQUE")
    print("Constraints setup complete.")

if __name__ == "__main__":
    setup_constraints()
