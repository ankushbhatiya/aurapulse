from neo4j import GraphDatabase
from api.config import settings

def setup_constraints():
    driver = GraphDatabase.driver(
        settings.NEO4J_URI, 
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD) if settings.NEO4J_PASSWORD else None
    )
    
    labels = ["Person", "Organization", "Policy", "Concept", "Event", "Brand", "Celebrity"]
    
    with driver as drv:
        with drv.session() as session:
            print("🚀 Setting up Neo4j Constraints & Indexes...")
            
            for label in labels:
                try:
                    # Create a composite unique constraint on name and tenant_id
                    # This also creates a composite index
                    query = f"CREATE CONSTRAINT {label.lower()}_name_tenant_unique IF NOT EXISTS FOR (n:{label}) REQUIRE (n.name, n.tenant_id) IS UNIQUE"
                    session.run(query)
                    print(f"✅ Constraint created for :{label}(name, tenant_id)")
                    
                    # Also create a single-property index for tenant_id for fast filtering when name isn't known
                    index_query = f"CREATE INDEX {label.lower()}_tenant_idx IF NOT EXISTS FOR (n:{label}) ON (n.tenant_id)"
                    session.run(index_query)
                    print(f"✅ Index created for :{label}(tenant_id)")
                except Exception as e:
                    print(f"⚠️  Could not create constraint/index for {label}: {e}")

    print("✨ Graph optimization complete.")

if __name__ == "__main__":
    setup_constraints()
