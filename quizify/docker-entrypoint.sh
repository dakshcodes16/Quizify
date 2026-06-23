#!/bin/bash
# Starts the FastAPI auth/data service in the background and the
# Streamlit UI in the foreground (so the container's main process
# exits cleanly if either crashes hard enough).
set -e

echo "Starting Quizify API (FastAPI) on port 8000..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Give the API a moment to come up before Streamlit starts hitting it
sleep 2

echo "Starting Quizify UI (Streamlit) on port 8501..."
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true &
UI_PID=$!

# If either process dies, bring the whole container down
wait -n $API_PID $UI_PID
exit $?
