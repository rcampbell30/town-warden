#!/bin/bash
set -e

export ENVIRONMENT=${ENVIRONMENT:-local}
export TOWN_CONFIG=${TOWN_CONFIG:-config/towns/blackpool.json}
export ALLOW_SIMULATION=${ALLOW_SIMULATION:-true}

cd backend
uvicorn main:app --host localhost --port 8000 &
BACKEND_PID=$!

cd ..
python -m http.server 5000 --directory frontend --bind 0.0.0.0 &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

wait $BACKEND_PID $FRONTEND_PID
