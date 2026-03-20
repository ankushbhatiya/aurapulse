import os
import json
import time
from engine.llm import STRATEGIC_LLM, LLM_BASE_URL, r
from typing import List, Dict
from litellm import completion
from litellm.exceptions import RateLimitError
from dotenv import load_dotenv

# Load global config
CONFIG_PATH = "/Users/ankush/.aura/aura.cfg"
load_dotenv(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else load_dotenv("/app/.aura/aura.cfg")

class ReportAgent:
    def __init__(self):
        self.redis_client = r
        self.app_env = os.getenv("APP_ENV", "development")

    def generate_report(self, track_id: str, simulation_data: List[Dict]) -> Dict:
        """
        Analyzes the full simulation log and generates a strategic ROI report.
        """
        if not simulation_data:
            return {"error": "No data found for track"}

        # Get simulation metadata to find the original post for this track
        sim_id = simulation_data[0].get("simulation_id")
        meta = self.redis_client.hgetall(f"sim:{sim_id}:meta")
        
        post_text = ""
        if meta:
            post_key = b"postA" if track_id == "TrackA" else b"postB"
            post_text = meta.get(post_key, b"").decode("utf-8")

        # Prepare summary for LLM
        swarm_summary = "\n".join([
            f"- {msg['persona_name']} ({msg['bias']}): {msg['comment']}" 
            for msg in simulation_data[:50]
        ])

        system_prompt = f"""
        You are a Senior PR Analyst. Your task is to analyze simulation logs for a SPECIFIC social media post.
        
        ### TRACK CONTEXT
        Analyzing results for: {track_id}
        Original Post Content: "{post_text}"
        
        ### ANALYSIS GOAL
        Observe how the swarm reacted to THIS specific post. 
        Identify unique risks, viral potential, and sentiment shifts specific to this content.
        
        CRITICAL: You MUST output valid JSON ONLY. 
        Required JSON keys:
        - "viral_momentum": (int 0-100)
        - "controversy_risk": (int 0-100)
        - "community_drift": (int 0-100)
        - "confidence_score": (int 0-100) -> Calculate based on swarm consistency. Higher if the swarm converges on a single sentiment, lower if they are split or confused.
        - "top_risk_factor": (string, 1 sentence)
        - "sentiment_summary": (string, 1 sentence)
        
        ### SCORING RULES
        - Be precise. Avoid round numbers like 50, 75, 80 unless they truly fit. 
        - Track A and Track B results MUST be independent. Do not repeat scores from previous analyses.
        """

        user_prompt = f"""
        ### SIMULATION LOG FOR {track_id}
        {swarm_summary}
        
        Output the JSON analysis now:
        """

        for attempt in range(3):
            try:
                response = completion(
                    model=STRATEGIC_LLM,
                    api_base=LLM_BASE_URL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000,
                    response_format=None # Ensure no automatic JSON mode is triggered
                )
                content = response.choices[0].message.content.strip()
                
                # Robust JSON cleaning
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                if not content.startswith("{"):
                    start = content.find("{")
                    end = content.rfind("}")
                    if start != -1 and end != -1:
                        content = content[start : end + 1]
                    else:
                        lines = [l.strip() for l in content.split('\n') if l.strip()]
                        if lines:
                            last_line = lines[-1]
                            if last_line.startswith("{"):
                                content = last_line
                            elif "{" in last_line:
                                content = last_line[last_line.find("{"):]

                return json.loads(content)
            except RateLimitError:
                time.sleep(2 ** attempt)
            except Exception as e:
                print(f"Report Generation Attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return {
                        "viral_momentum": 0,
                        "controversy_risk": 0,
                        "community_drift": 0,
                        "confidence_score": 0,
                        "top_risk_factor": f"Error: {str(e)}",
                        "sentiment_summary": "Analysis failed after 3 attempts."
                    }
        return {"error": "Unknown failure"}

if __name__ == "__main__":
    # Test with mock data
    agent = ReportAgent()
    mock_data = [
        {"persona_name": "User_1", "bias": "Hater", "comment": "This is terrible, I hate it."},
        {"persona_name": "User_2", "bias": "Super-fan", "comment": "Amazing! Love the sustainability."}
    ]
    print(agent.generate_report("TestTrack", mock_data))
