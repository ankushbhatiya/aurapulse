![AuraPulse Banner](images/banner.svg)

# AuraPulse: Predictive Social Simulation Engine

AuraPulse is a high-stakes social media simulation sandbox inspired by the **MiroFish** architecture. It allows talent managers and PR teams to run parallel, multi-turn AI simulations to predict audience reactions to social media posts, acting as an insurance policy against PR disasters.

## 📸 Dashboard Preview

![AuraPulse Dashboard](images/aura_run.png)

## 🚀 Key Features

- **The "God View" Dashboard:** A real-time, three-column layout for simulation setup, live feed, and predictive analytics.
- **MiroFish OASIS Engine:** A sophisticated multi-agent framework where "Digital Twin" personas interact with each other in multi-turn simulations.
- **Parallel A/B Testing:** Compare two post versions (Track A vs. Track B) simultaneously in a single simulation run.
- **GraphRAG-Powered Grounding:** Automated Neo4j pipeline that extracts brand guidelines into a knowledge graph to ground AI agent behavior.
- **ReportAgent Analytics:** LLM-powered PR analyst that synthesizes thousands of comments into actionable ROI and Risk reports.
- **Multi-Session Persistence:** Backend-persisted drafts and simulation history, allowing multiple users or tabs to work independently without data loss.

## 🛠 Tech Stack

### Frontend
- **Framework:** Next.js 15+ (App Router)
- **Styling:** Tailwind CSS (Custom Dark/Light Themes)
- **UI Components:** Shadcn/UI & Lucide Icons
- **Real-time:** Server-Sent Events (SSE)

### Backend
- **API:** FastAPI (Python 3.9+)
- **Task Queue:** Celery with Redis (Optimized with `solo` pool for async stability)
- **LLM Orchestration:** LiteLLM (Supporting local servers like Minimax-m2.5)
- **Database:** Neo4j (Knowledge Graph)
- **Cache/State:** Redis (Drafts, History, Reports)

## 🚦 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.9+
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
   export PYTHONPATH=$PYTHONPATH:.
   uvicorn api.main:app --reload --port 8000
   ```

2. **Start Celery Worker (Terminal 2):**
   ```bash
   cd backend
   source venv/bin/activate
   export PYTHONPATH=$PYTHONPATH:.
   celery -A engine.celery_app worker --loglevel=info -P solo
   ```

3. **Start Frontend (Terminal 3):**
   ```bash
   cd ui
   npm run dev
   ```

Access the dashboard at `http://localhost:3000`.

## 📜 License
Internal Use Only.
