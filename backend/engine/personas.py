import json
import uuid
import random
import os

def generate_personas(count=20):
    biases = ["Super-fan", "Hater", "Casual Observer", "Activist", "Investor"]
    demographics = ["Gen Z", "Millennial", "Gen X", "Boomer"]
    
    personas = []
    for i in range(count):
        personas.append({
            "id": str(uuid.uuid4()),
            "name": f"User_{i+100}",
            "bias": random.choice(biases),
            "demographic": random.choice(demographics),
            "vibe": random.choice(["Supportive", "Critical", "Funny", "Aggressive", "Neutral"])
        })
    
    file_path = os.path.join(os.path.dirname(__file__), "personas.json")
    with open(file_path, "w") as f:
        json.dump(personas, f, indent=2)
    print(f"Generated {count} personas in {file_path}")

if __name__ == "__main__":
    generate_personas()
