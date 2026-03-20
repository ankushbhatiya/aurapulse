import requests
import time
import uuid

BASE_URL = "http://localhost:8000"

def test_1_knowledge_ingestion():
    """Verify that we can ingest raw text into the knowledge graph."""
    payload = {
        "text": "Aura is a famous environmentalist who recently launched Earth-First fashion.",
        "client_id": "test_e2e_tenant"
    }
    response = requests.post(f"{BASE_URL}/ingest", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "Ingestion complete"

def test_2_simulation_trigger():
    """Verify that we can trigger a dual-track simulation."""
    payload = {
        "postA": "I love nature.",
        "postB": "I love fast cars.",
        "agent_count": 1 # Minimal count for plumbing test
    }
    response = requests.post(f"{BASE_URL}/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "simulation_id" in data

def test_3_history_and_logs():
    """Verify that simulation data is being recorded in Redis."""
    # 1. Trigger
    payload = {
        "postA": "Test History A",
        "postB": "Test History B",
        "agent_count": 1
    }
    response = requests.post(f"{BASE_URL}/simulate", json=payload)
    sim_id = response.json()["simulation_id"]
    
    print(f"Waiting for simulation {sim_id} to process...")
    # Wait for 1 agent * 2 turns = 2 LLM calls per track
    time.sleep(20) 
    
    # 2. Check History List
    res_list = requests.get(f"{BASE_URL}/simulations")
    assert res_list.status_code == 200
    history = res_list.json()
    assert any(sim["id"] == sim_id for sim in history)
    
    # 3. Check specific logs
    res_logs = requests.get(f"{BASE_URL}/history/{sim_id}/TrackA")
    assert res_logs.status_code == 200
    logs = res_logs.json()
    assert len(logs) > 0
    print(f"Verified {len(logs)} comments for {sim_id}")

def test_4_draft_persistence():
    """Verify that drafts are saved and retrieved correctly per session."""
    session_id = str(uuid.uuid4())
    payload = {
        "session_id": session_id,
        "postA": "Draft A Content",
        "postB": "Draft B Content",
        "agent_count": 1
    }
    
    # 1. Save
    save_res = requests.post(f"{BASE_URL}/draft", json=payload)
    assert save_res.status_code == 200
    
    # 2. Retrieve
    get_res = requests.get(f"{BASE_URL}/draft/{session_id}")
    assert get_res.status_code == 200
    draft = get_res.json()
    assert draft["postA"] == "Draft A Content"
    assert draft["agent_count"] == 1
