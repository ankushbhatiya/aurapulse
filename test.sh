#!/bin/bash

# AuraPulse Automated Test Launcher
# This script starts the dev environment, runs E2E tests, and cleans up.

set -e

echo "🧪 Starting Automated End-to-End Testing..."

# 1. Start everything using dev.sh logic but in background
echo "🚀 Launching development stack..."
# We use a modified version of dev.sh logic to ensure it doesn't block
./dev.sh & 
DEV_PID=$!

# 2. Wait for services to be ready
echo "⏳ Waiting for services to stabilize (30s)..."
sleep 30

# 3. Run Tests
echo "🏃 Running Pytest suite..."
cd backend
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
pytest ../tests/test_e2e.py || TEST_EXIT_CODE=$?

# 4. Cleanup
echo "🧹 Cleaning up background processes..."
pkill -f uvicorn || true
pkill -f celery || true
pkill -f next || true

if [ -z "$TEST_EXIT_CODE" ]; then
    echo "✅ SUCCESS: All tests passed."
    exit 0
else
    echo "❌ FAILURE: Some tests failed with exit code $TEST_EXIT_CODE."
    exit $TEST_EXIT_CODE
fi
