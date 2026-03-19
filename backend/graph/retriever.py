import os
from typing import List
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

def get_context_for_post(post_text: str, client_id: str = "CLIENT_A") -> str:
    """
    Fetches multi-hop context from Neo4j based on entities mentioned in the post.
    Matches mentions against node names and returns their immediate relationships.
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # In a real app, we'd use an LLM to extract entities first.
    # For POC, we'll fetch all nodes for the tenant and check for substring matches.
    context_statements = []
    
    with driver.session() as session:
        # 1. Fetch all entity names for this tenant
        nodes_result = session.run(
            "MATCH (n) WHERE n.tenant_id = $client_id RETURN n.name as name, labels(n)[0] as type",
            client_id=client_id
        )
        entities = [{"name": r["name"], "type": r["type"]} for r in nodes_result]
        
        # 2. Identify mentioned entities
        mentioned = [e for e in entities if e["name"].lower() in post_text.lower()]
        
        if not mentioned:
            # Fallback: Just get general celebrity context
            celeb_result = session.run(
                "MATCH (c:Celebrity {id: $client_id})-[r]->(n) RETURN n.name as target, type(r) as rel, r.description as desc, labels(n)[0] as type",
                client_id=client_id
            )
            for r in celeb_result:
                context_statements.append(f"Celebrity {r['rel']} {r['target']} ({r['desc'] or ''})")
        else:
            # 3. Fetch relationships for mentioned entities
            for ent in mentioned:
                rel_result = session.run(
                    """
                    MATCH (n {name: $name})-[r]-(m)
                    WHERE n.tenant_id = $client_id AND (m.tenant_id = $client_id OR m:Celebrity)
                    RETURN n.name as source, type(r) as rel, m.name as target, r.description as desc
                    LIMIT 5
                    """,
                    name=ent["name"], client_id=client_id
                )
                for r in rel_result:
                    desc = f" ({r['desc']})" if r['desc'] else ""
                    context_statements.append(f"{r['source']} {r['rel']} {r['target']}{desc}")

    driver.close()
    
    if not context_statements:
        return "No specific historical brand context triggered for this post."
        
    return " | ".join(list(set(context_statements))) # Deduplicate

if __name__ == "__main__":
    # Test call
    print(f"Context: {get_context_for_post('What about Celeb X and Beyond Meat?')}")
