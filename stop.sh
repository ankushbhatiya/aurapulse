#!/bin/bash

# AuraPulse Stop Script
# This script shuts down the backend, worker, UI, and Docker infrastructure.

echo "🛑 Stopping AuraPulse Development Environment..."

# 1. Stop Local Processes
echo "🔌 Killing local processes (Backend, Worker, UI)..."
pkill -f uvicorn || true
pkill -f celery || true
pkill -f "next-router-worker" || true
pkill -f "node.*next" || true

# 2. Stop Docker Infrastructure
echo "🐳 Stopping Docker containers..."
if [ -f "$HOME/.aura/aura.cfg" ]; then
    docker-compose --env-file "$HOME/.aura/aura.cfg" stop
else
    docker-compose stop
fi

echo "✅ All services stopped."
