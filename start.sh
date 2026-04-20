#!/bin/bash
set -e
cd "$(dirname "$0")"

mkdir -p logs

# ──────────────────────────────────────────────────────────────
# 0. 포트 정리 (기존 프로세스가 점유 중이면 종료)
# ──────────────────────────────────────────────────────────────
for port in 8001 5173 8085 4000; do
  pid=$(lsof -ti ":$port" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    echo "Port $port was busy (PID $pid) — killing"
    kill -9 "$pid" 2>/dev/null || true
    sleep 0.5
  fi
done

# ──────────────────────────────────────────────────────────────
# 1. Backend (FastAPI) :8001
# ──────────────────────────────────────────────────────────────
echo "[1/4] Preparing backend..."
cd backend
if [ ! -d ".venv" ]; then
  echo "  → .venv가 없습니다. 생성 중..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[dev]" > ../logs/backend-install.log 2>&1
  echo "  → 설치 완료 (logs/backend-install.log)"
else
  source .venv/bin/activate
fi

echo "  → Starting uvicorn on :8001..."
uvicorn app.main:app --reload --port 8001 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# ──────────────────────────────────────────────────────────────
# 2. Frontend (Vite, React) :5173
# ──────────────────────────────────────────────────────────────
echo "[2/4] Preparing frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
  echo "  → node_modules가 없습니다. npm install 실행 중..."
  npm install > ../logs/frontend-install.log 2>&1
  echo "  → 설치 완료 (logs/frontend-install.log)"
fi

echo "  → Starting Vite on :5173..."
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# ──────────────────────────────────────────────────────────────
# 3. pfy-front (Vue Mockup 런타임) :8085
# ──────────────────────────────────────────────────────────────
PFY_PID=""
if [ -d "pfy-front" ]; then
  echo "[3/4] Preparing pfy-front..."
  cd pfy-front
  if [ ! -d "node_modules" ] || [ ! -x "node_modules/.bin/vite" ]; then
    echo "  → node_modules/vite가 없습니다. npm install 실행 중..."
    if ! npm install --legacy-peer-deps > ../logs/pfy-front-install.log 2>&1; then
      echo "  → 사내 registry 실패, public registry 시도..."
      npm install --registry=https://registry.npmjs.org/ --legacy-peer-deps >> ../logs/pfy-front-install.log 2>&1
    fi
    echo "  → 설치 완료 (logs/pfy-front-install.log)"
  fi

  echo "  → Starting pfy-front Vite on :8085..."
  npm run dev > ../logs/pfy-front.log 2>&1 &
  PFY_PID=$!
  cd ..
fi

# ──────────────────────────────────────────────────────────────
# 4. pfy-front scaffolding server (Express, MockupBuilder API) :4000
# ──────────────────────────────────────────────────────────────
SCAFFOLD_PID=""
if [ -d "pfy-front/scaffolding" ]; then
  echo "[4/4] Preparing pfy-front scaffolding..."
  cd pfy-front/scaffolding
  if [ ! -d "node_modules" ] || [ ! -x "node_modules/.bin/ts-node" ]; then
    echo "  → node_modules/ts-node가 없습니다. npm install 실행 중..."
    if ! npm install --legacy-peer-deps > ../../logs/scaffolding-install.log 2>&1; then
      echo "  → 사내 registry 실패, public registry 시도..."
      npm install --registry=https://registry.npmjs.org/ --legacy-peer-deps >> ../../logs/scaffolding-install.log 2>&1
    fi
    echo "  → 설치 완료 (logs/scaffolding-install.log)"
  fi
  # scaffolding/.env 필요 (AOAI_ENDPOINT, AOAI_API_KEY)
  if [ ! -f ".env" ]; then
    echo "  ⚠ scaffolding/.env 파일이 없습니다. AI 기능은 동작하지 않습니다."
    echo "    pfy-front/scaffolding/.env.example 을 참고하세요."
  fi
  echo "  → Starting scaffolding Express on :4000..."
  npm run dev > ../../logs/scaffolding.log 2>&1 &
  SCAFFOLD_PID=$!
  cd ../..
fi

# ──────────────────────────────────────────────────────────────
# PID 저장 및 요약 출력
# ──────────────────────────────────────────────────────────────
echo "$BACKEND_PID" > .pids
echo "$FRONTEND_PID" >> .pids
[ -n "$PFY_PID" ] && echo "$PFY_PID" >> .pids
[ -n "$SCAFFOLD_PID" ] && echo "$SCAFFOLD_PID" >> .pids

echo ""
echo "═══════════════════════════════════════════════════════════"
echo " Services Running"
echo "═══════════════════════════════════════════════════════════"
echo "  Backend      http://localhost:8001   (PID $BACKEND_PID)"
echo "  Frontend     http://localhost:5173   (PID $FRONTEND_PID)"
[ -n "$PFY_PID" ]      && echo "  pfy-front    http://localhost:8085   (PID $PFY_PID)"
[ -n "$SCAFFOLD_PID" ] && echo "  scaffolding  http://localhost:4000   (PID $SCAFFOLD_PID)"
echo ""
echo "  Logs:  tail -f logs/<backend|frontend|pfy-front|scaffolding>.log"
echo "  Stop:  ./stop.sh"
echo "═══════════════════════════════════════════════════════════"

# ──────────────────────────────────────────────────────────────
# Frontend가 준비되면 브라우저 자동 오픈 (최대 30초 대기)
# ──────────────────────────────────────────────────────────────
(
  for i in $(seq 1 30); do
    if curl -s -o /dev/null -w "%{http_code}" --max-time 1 http://localhost:5173/ 2>/dev/null | grep -q "200"; then
      case "$(uname -s)" in
        Darwin) open http://localhost:5173/ ;;
        Linux)  xdg-open http://localhost:5173/ > /dev/null 2>&1 || true ;;
      esac
      break
    fi
    sleep 1
  done
) &

wait
