import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))

def get_context_for_post(post_text: str, client_id: str = "CLIENT_A") -> str:
    # In a real app, this would use an LLM to extract keywords.
    # For the POC, we use a simple list check.
    keywords = ["Veganism", "Politics", "Fashion"]
    found_concepts = [k for k in keywords if k.lower() in post_text.lower()]
    
    if not found_concepts:
        return "No specific historical brand context triggered for this post."

    context_statements = []
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            for concept in found_concepts:
                query = """
                MATCH (c:Celebrity {id: $client_id})-[r:BELIEVES]->(con:Concept {name: $concept})
                RETURN r.stance AS stance
                """
                result = session.run(query, client_id=client_id, concept=concept)
                for record in result:
                    context_statements.append(f"Regarding {concept}: {record['stance']}")
    
    return " | ".join(context_statements)

if __name__ == "__main__":
    # Test call
    print(f"Context: {get_context_for_post('I think veganism is the future of fashion.')}")
