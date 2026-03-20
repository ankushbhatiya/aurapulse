#!/bin/bash

# AuraPulse Development Setup & Launcher
# This script starts the entire stack for local development.

set -e

echo "🚀 Starting AuraPulse Development Environment..."

# 1. Start Infrastructure (Redis, Neo4j)
echo "📦 Spinning up Docker infrastructure..."
docker-compose up -d

# 2. Setup Backend
echo "🐍 Preparing Backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$PYTHONPATH:.

# Create logs directory if it doesn't exist
mkdir -p ~/.aura

# Kill existing local processes if any
pkill -f uvicorn || true
pkill -f celery || true

# 3. Start Backend & Worker
echo "⚙️  Starting FastAPI Backend & Celery Worker..."
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 > ~/.aura/backend.log 2>&1 &
celery -A engine.celery_app worker --loglevel=info -P solo > ~/.aura/celery.log 2>&1 &

# 4. Setup & Start UI
echo "🎨 Starting Frontend UI..."
cd ../ui
if [ ! -d "node_modules" ]; then
    echo "Installing UI dependencies..."
    npm install
fi

# We don't background the UI so we can see the output and stop everything with Ctrl+C
echo "✅ System is live! Access dashboard at http://localhost:3000"
echo "💡 Press Ctrl+C to stop the UI (Backend & Worker will keep running in background)."
npm run dev
