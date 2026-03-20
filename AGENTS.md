# AuraPulse: Agent Engineering Guide

## 🎭 Design Philosophy
AuraPulse is not a chatbot; it is a **Societal Mirror**. Every development step must focus on the emergent behavior of the swarm. We prioritize **Grounded Authenticity** over generic AI helpfulness.

### The "MiroFish" Core
We follow the MiroFish architecture: 
1. **Knowledge (The Past):** Stored in Neo4j via GraphRAG. Agents must be grounded in facts before they speak.
2. **Memory (The Self):** Stored in Zep Cloud. Agents must maintain a consistent personality across simulations.
3. **Simulation (The Now):** Parallelized OASIS engine. Speed and concurrency are critical.

---

## 🛠 Development Guardrails

### 1. The Global Config Source of Truth
NEVER hardcode secrets or paths. Always use `~/.aura/aura.cfg`. 
*   When adding new environment variables, update the template in `aura.cfg` and the Docker mount logic in `docker-compose.prod.yml`.
*   Ensure absolute paths are used for `load_dotenv` to support Celery workers running in varying environments.

### 2. Async-First Workers
The simulation is high-concurrency. 
*   Always use `redis.asyncio` for engine-to-UI communication.
*   Use `asyncio.Semaphore` to protect local LLM servers from being overwhelmed.
*   Celery workers must use the `solo` pool on macOS to avoid `SIGSEGV` errors with nested event loops.

### 3. Namespaced Data Isolation
Data integrity is paramount. 
*   **Redis:** `REDIS_DB=1` for development, `REDIS_DB=0` for production.
*   **Neo4j:** Every node MUST have a `tenant_id` (usually `development` or `production`). 
*   Filtering by environment must happen at the database query level.

---

## 🧪 Verification Protocol

A feature is only "Done" when it passes the end-to-end plumbing check. **Manual testing is not enough.**

### Mandatory Test Step:
Before submitting any code change, you MUST run:
```bash
./test.sh
```
This script validates:
1.  **Plumbing:** Can the API talk to the databases?
2.  **Simulation:** Can the worker trigger an LLM and log the result?
3.  **Persistence:** Are the results reloadable from the History sidebar?

---

## 🚀 Vision for the Future
AuraPulse will evolve from predicting *reactions* to recommending *strategies*. Future versions should:
*   Integrate real-time social media scraping to update the GraphRAG dynamically.
*   Use the `ReportAgent` to suggest specific edits to Post B to maximize ROI.
*   Expand the Swarm to 1,000+ truly diverse digital twins.

**Stay grounded. Keep the swarm consistent.**
