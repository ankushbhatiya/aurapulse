import os
import json
import redis
from typing import List, Dict
from litellm import completion
from dotenv import load_dotenv

load_dotenv()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/minimax/minimax-m2.5")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1/")

class ReportAgent:
    def __init__(self):
        self.redis_client = redis.Redis.from_url(REDIS_URL)

    def generate_report(self, track_id: str, simulation_data: List[Dict]) -> Dict:
        """
        Analyzes the full simulation log and generates a strategic ROI report.
        """
        if not simulation_data:
            return {"error": "No data found for track"}

        # Prepare summary for LLM
        swarm_summary = "\n".join([
            f"- {msg['persona_name']} ({msg['bias']}): {msg['comment']}" 
            for msg in simulation_data[:50] # Limit to 50 for token constraints
        ])

        prompt = f"""
        ### TASK
        You are a Senior PR Analyst. Analyze the following AI-agent simulation log for a social media post.
        
        ### SIMULATION LOG
        {swarm_summary}
        
        ### ANALYSIS REQUIREMENTS
        Output valid JSON ONLY with the following keys:
        - "viral_momentum": (int 0-100)
        - "controversy_risk": (int 0-100)
        - "community_drift": (int 0-100)
        - "confidence_score": (int 0-100)
        - "top_risk_factor": (string, 1 sentence)
        - "sentiment_summary": (string, 1 sentence)
        
        ### RESPONSE
        """

        try:
            response = completion(
                model=LLM_MODEL,
                api_base=LLM_BASE_URL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            content = response.choices[0].message.content.strip()
            
            # Robust JSON cleaning
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            if not content.startswith("{"):
                content = content[content.find("{"):]
            if not content.endswith("}"):
                content = content[:content.rfind("}")+1]

            return json.loads(content)
        except Exception as e:
            print(f"Report Generation Error: {e}")
            return {
                "viral_momentum": 0,
                "controversy_risk": 0,
                "community_drift": 0,
                "confidence_score": 0,
                "top_risk_factor": "Error generating report.",
                "sentiment_summary": "Simulation analysis failed."
            }

if __name__ == "__main__":
    # Test with mock data
    agent = ReportAgent()
    mock_data = [
        {"persona_name": "User_1", "bias": "Hater", "comment": "This is terrible, I hate it."},
        {"persona_name": "User_2", "bias": "Super-fan", "comment": "Amazing! Love the sustainability."}
    ]
    print(agent.generate_report("TestTrack", mock_data))
