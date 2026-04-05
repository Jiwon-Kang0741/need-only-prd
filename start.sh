#!/bin/bash
cd "$(dirname "$0")"

echo "Starting backend on :8001..."
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001 &
BACKEND_PID=$!
cd ..

echo "Starting frontend on :5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "$BACKEND_PID" > .pids
echo "$FRONTEND_PID" >> .pids

echo "Backend PID: $BACKEND_PID (port 8001)"
echo "Frontend PID: $FRONTEND_PID (port 5173)"
echo "Run ./stop.sh to stop both servers."
wait
