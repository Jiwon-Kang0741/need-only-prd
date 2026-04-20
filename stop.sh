#!/bin/bash
cd "$(dirname "$0")"

if [ -f .pids ]; then
  while read -r pid; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
      echo "Stopped PID $pid"
    fi
  done < .pids
  rm .pids
fi

# Kill any remaining processes on the ports (8001 backend, 5173 frontend, 8085 pfy-front)
for port in 8001 5173 8085; do
  pid=$(lsof -ti ":$port" 2>/dev/null)
  if [ -n "$pid" ]; then
    kill "$pid" 2>/dev/null
    echo "Stopped process on port $port (PID $pid)"
  fi
done

echo "All servers stopped."
