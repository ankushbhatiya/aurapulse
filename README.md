# AuraPulse: Predictive Social Simulation Engine

AuraPulse is a high-stakes social media simulation sandbox designed for talent managers and PR teams. It allows users to run parallel AI-driven simulations to predict audience reactions to social media posts before they go live, acting as an "insurance policy" against PR disasters.

## 🚀 Key Features

- **The "God View" Live Sandbox:** A real-time, three-column dashboard to manage simulations.
- **Parallel A/B Testing:** Compare two different post versions (Track A vs. Track B) simultaneously.
- **GraphRAG-Powered Context:** Uses Neo4j and Knowledge Graphs to ground AI agents in a celebrity's specific brand history and guidelines.
- **Digital Twin Swarms:** Simulate 1,000+ distinct agent personas (fans, haters, activists, etc.) reacting in real-time.
- **Predictive Analytics:** Get actionable insights, including Sentiment Delta, Brand Risk, and Marginal Utility Scores.

## 🛠 Tech Stack

### Frontend
- **Framework:** Next.js 15+ (App Router)
- **Styling:** Tailwind CSS
- **UI Components:** Shadcn/UI
- **Real-time:** Server-Sent Events (SSE)

### Backend
- **API:** FastAPI (Python 3.10+)
- **Task Queue:** Celery with Redis
- **LLM Orchestration:** LiteLLM (supporting GPT-4o-mini, Llama-3, etc.)
- **Memory:** Zep Cloud / VectorDB for agent consistency

### Database & Knowledge Graph
- **Graph Database:** Neo4j (GraphRAG)
- **Cache/Pub-Sub:** Redis

## 🏗 Project Structure

```text
/aurapulse
  ├── backend/          # FastAPI & Celery Logic
  │   ├── api/          # REST Endpoints
  │   ├── engine/       # Simulation & Agent Swarm Logic
  │   └── graph/        # Neo4j & Retrieval Layer
  ├── ui/               # Next.js Frontend
  ├── docker-compose.yml # Infrastructure (Redis, Neo4j)
  └── .env              # Environment Variables
```

## 🚦 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+

### Setup

1. **Start Infrastructure:**
   ```bash
   docker-compose up -d
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup:**
   ```bash
   cd ui
   npm install
   ```

### Running the Application

1. **Start Backend (Terminal 1):**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn api.main:app --reload --port 8000
   ```

2. **Start Celery Worker (Terminal 2):**
   ```bash
   cd backend
   source venv/bin/activate
   celery -A engine.celery_app worker --loglevel=info
   ```

3. **Start Frontend (Terminal 3):**
   ```bash
   cd ui
   npm run dev
   ```

Access the dashboard at `http://localhost:3000`.

## 📜 License
Internal Use Only.
