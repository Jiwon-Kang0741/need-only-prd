#!/bin/bash
cd "$(dirname "$0")"

# 1) Try the saved PID list first (graceful shutdown).
if [ -f .pids ]; then
  while read -r pid; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
      echo "Stopped PID $pid"
    fi
  done < .pids
  rm -f .pids
fi

# 2) Force-cleanup anything still bound to the dev ports, including the
#    full process tree. uvicorn --reload spawns a watchfiles parent + a
#    multiprocessing-fork child, both of which need to die or the listening
#    socket leaks across runs (this is what created the 8-instance pile-up
#    we saw on Windows).
if command -v lsof >/dev/null 2>&1; then
  for port in 8001 5173 8085 4000; do
    pids=$(lsof -ti ":$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
      for pid in $pids; do
        kill -9 "$pid" 2>/dev/null || true
        echo "Stopped process on port $port (PID $pid)"
      done
    fi
  done
elif command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
    function Kill-Tree([int]\$RootId) {
      try {
        \$kids = Get-CimInstance Win32_Process -Filter \"ParentProcessId=\$RootId\" -ErrorAction SilentlyContinue
        foreach (\$k in \$kids) { Kill-Tree -RootId \$k.ProcessId }
        Stop-Process -Id \$RootId -Force -ErrorAction SilentlyContinue
      } catch {}
    }
    foreach (\$pass in 1..3) {
      \$any = \$false
      foreach (\$port in 8001,5173,8085,4000) {
        \$conns = Get-NetTCPConnection -LocalPort \$port -State Listen -ErrorAction SilentlyContinue
        foreach (\$c in \$conns) {
          \$any = \$true
          Write-Host (\"Stopped process on port {0} (PID {1})\" -f \$port, \$c.OwningProcess)
          Kill-Tree -RootId \$c.OwningProcess
        }
      }
      if (-not \$any) { break }
      Start-Sleep -Milliseconds 800
    }
  " 2>/dev/null || true
fi

echo "All servers stopped."
