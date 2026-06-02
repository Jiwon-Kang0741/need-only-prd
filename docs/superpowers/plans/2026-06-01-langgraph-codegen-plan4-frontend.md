# LangGraph Codegen — Plan 4: Frontend Event Redesign

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프론트엔드(types/store/panel)를 LangGraph 신규 SSE 이벤트 포맷에 맞춰 재설계한다. node/wave 진행, ReAct tool_call, 신규 file_complete(path) + 완료 후 /files 조회를 반영.

**Architecture:** 백엔드가 보내는 신규 이벤트(node_start/node_end, wave_start/wave_complete, contract, plan{files}, file_complete{path}, tool_call/tool_result, react_step, complete, error, log)를 `SSEEvent` 타입에 추가하고, sessionStore의 generateCode 핸들러를 신규 이벤트로 교체한다. file_complete는 content를 싣지 않으므로 complete 시 `/api/codegen/files`로 최종 파일을 가져온다. CodeGenPanel은 wave 진행 + ReAct 타임라인을 표시한다.

**Tech Stack:** React 19, TypeScript, Zustand, Vite, Tailwind v4

**참조 설계:** `docs/superpowers/specs/2026-06-01-langgraph-agentic-codegen-design.md` (섹션 6)
**선행:** Plan 3 (백엔드 신규 이벤트 송출, `/api/codegen/files` 존재)

**검증:** 프론트는 자동 테스트 인프라가 없으므로 `npm run build`(type-check) 통과 + 수동 확인을 검증 기준으로 한다. 각 task는 빌드 통과를 확인하고 커밋.

---

## File Structure

### 수정
- `frontend/src/types/index.ts` — SSEEvent 신규 타입 + CodeGenState 진행 상태 필드 추가
- `frontend/src/store/sessionStore.ts` — generateCode 핸들러 신규 이벤트로 교체 + fetchFiles
- `frontend/src/api/client.ts` — `getGeneratedFiles` API 함수 추가 (없으면)
- `frontend/src/components/CodeGenPanel.tsx` — wave 진행 + ReAct 타임라인 표시

---

## Task 1: SSEEvent + CodeGenState 타입 확장

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: SSEEvent 타입에 신규 이벤트 추가**

`frontend/src/types/index.ts`의 `SSEEvent` 인터페이스를 찾아, `type` 유니온과 필드를 교체:

```typescript
export interface SSEEvent {
  type: 'status' | 'text' | 'chunk' | 'requirements' | 'complete' | 'error'
      | 'plan' | 'file_start' | 'file_complete' | 'log'
      | 'agent_start' | 'agent_complete'
      // LangGraph agentic events
      | 'node_start' | 'node_end'
      | 'wave_start' | 'wave_complete'
      | 'contract'
      | 'tool_call' | 'tool_result'
      | 'react_step' | 'react_converged'
      | 'graph_complete'
  content?: string
  spec_version?: number
  message?: string
  // codegen fields
  plan?: CodeGenPlan
  index?: number
  total?: number
  file_path?: string
  file_type?: string
  layer?: string
  description?: string
  line?: string
  status?: Record<string, unknown>
  ports?: { db?: number; backend?: number; frontend?: number }
  agent?: string
  display_name?: string
  files_count?: number
  // LangGraph agentic fields
  node?: string
  wave?: number
  file_count?: number
  path?: string
  tool?: string
  args?: Record<string, unknown>
  contract?: Record<string, unknown>
  files?: Array<{ file_path?: string; path?: string; file_type?: string; wave?: number }>
  iteration?: number
  thought?: string
  reason?: string
}
```

- [ ] **Step 2: CodeGenState에 진행 상태 필드 추가**

`CodeGenState` 인터페이스를 찾아 필드 추가 (기존 필드 유지, 끝에 추가):

```typescript
export interface CodeGenState {
  status: 'idle' | 'planning' | 'planned' | 'generating' | 'generated' | 'building' | 'running' | 'error'
  plan: CodeGenPlan | null
  generatedFiles: GeneratedFile[]
  currentFileIndex: number
  currentFileContent: string
  buildLogs: string[]
  error: string | null
  ports: { db?: number; backend?: number; frontend?: number } | null
  // LangGraph progress
  currentNode: string | null
  currentWave: number | null
  reactSteps: Array<{ iteration?: number; tool?: string; thought?: string }>
  plannedFiles: Array<{ path: string; file_type?: string; wave?: number }>
  completedPaths: string[]
}
```

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc -b 2>&1 | tail -20`
Expected: CodeGenState 신규 필드를 초기화하지 않은 곳에서 에러가 날 수 있음 → Task 2에서 initialCodeGen 갱신으로 해소. 이 단계는 타입 정의만이므로 SSEEvent 관련 에러는 없어야 함. (CodeGenState 초기화 에러만 남으면 정상)

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/types/index.ts
git commit -m "feat(frontend): add LangGraph SSE event types + codegen progress fields"
```

---

## Task 2: getGeneratedFiles API 함수

**Files:**
- Modify: `frontend/src/api/client.ts`

설계 참조: 신규 file_complete는 content를 싣지 않으므로(노드 도메인 이벤트), complete 후 `/api/codegen/files`로 최종 파일을 가져온다.

- [ ] **Step 1: client.ts에 getGeneratedFiles 추가**

`frontend/src/api/client.ts`의 `generateCode` 함수 근처(153행 부근)에 추가. 기존 fetch 패턴(consumeSSE는 SSE용이므로 일반 GET은 fetch 사용)을 따른다:

```typescript
export async function getGeneratedFiles(): Promise<
  Array<{ file_path: string; file_type: string; content: string; layer: string }>
> {
  const sessionId = getSessionId()
  const res = await fetch('/api/codegen/files', {
    headers: { 'X-Session-ID': sessionId },
  })
  if (!res.ok) return []
  const data = await res.json()
  return data.files ?? data ?? []
}
```

**주의:** `getSessionId`가 client.ts에 이미 있는지 확인. 없으면 기존 consumeSSE가 세션 헤더를 어떻게 넣는지 보고 동일 방식 사용.

- [ ] **Step 2: getSessionId 존재 확인**

Run: `cd frontend && grep -n "getSessionId\|X-Session-ID\|sessionStorage" src/api/client.ts | head`
Expected: 세션 ID 취득 방식 확인. 다르면 Step 1의 헤더 취득을 그 방식으로 맞춤.

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc -b 2>&1 | grep "client.ts" | head`
Expected: client.ts 관련 에러 없음 (CodeGenState 초기화 에러는 Task 3에서 해소)

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/api/client.ts
git commit -m "feat(frontend): add getGeneratedFiles API for post-complete file fetch"
```

---

## Task 3: sessionStore generateCode 핸들러 재작성

**Files:**
- Modify: `frontend/src/store/sessionStore.ts`

설계 참조: 신규 이벤트 핸들러. file_complete는 path만 → completedPaths에 기록. complete(graph) 시 getGeneratedFiles로 최종 파일 로드.

- [ ] **Step 1: initialCodeGen에 신규 필드 초기화**

`sessionStore.ts`의 `initialCodeGen` 정의(22행 부근)에 신규 필드 추가:

```typescript
const initialCodeGen: CodeGenState = {
  status: 'idle',
  plan: null,
  generatedFiles: [],
  currentFileIndex: 0,
  currentFileContent: '',
  buildLogs: [],
  error: null,
  ports: null,
  currentNode: null,
  currentWave: null,
  reactSteps: [],
  plannedFiles: [],
  completedPaths: [],
}
```

(기존 initialCodeGen에 이미 있는 필드는 그대로 두고 5개만 추가)

- [ ] **Step 2: import에 getGeneratedFiles 추가**

`sessionStore.ts` 상단 api import 블록에 추가:

```typescript
import { getGeneratedFiles } from '../api/client'
```

(기존 `import { ... } from '../api/client'` 묶음에 합쳐도 됨)

- [ ] **Step 3: generateCode 핸들러 본문 교체**

`generateCode:` 함수 내부 `apiGenerateCode((event) => { ... }, abort.signal)` 의 콜백 본문(187~251행, `if (event.type === 'status')`부터 마지막 `}` 직전까지)을 다음으로 교체:

```typescript
      if (abort.signal.aborted) return
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? event.message ?? null })
      } else if (event.type === 'node_start') {
        set((state) => ({
          codeGen: { ...state.codeGen, currentNode: event.node ?? null },
          statusMessage: `${event.node ?? 'graph'} 실행 중...`,
        }))
      } else if (event.type === 'node_end') {
        set((state) => ({ codeGen: { ...state.codeGen, currentNode: null } }))
      } else if (event.type === 'contract') {
        set({ statusMessage: '계약(contract) 추출 완료' })
      } else if (event.type === 'plan' && event.files) {
        set((state) => ({
          codeGen: {
            ...state.codeGen,
            plannedFiles: event.files!.map((f) => ({
              path: f.file_path ?? f.path ?? '',
              file_type: f.file_type,
              wave: f.wave,
            })),
          },
        }))
      } else if (event.type === 'wave_start') {
        set((state) => ({
          codeGen: { ...state.codeGen, currentWave: event.wave ?? null },
          statusMessage: `Wave ${event.wave} 생성 중 (${event.file_count ?? '?'}개 파일)...`,
        }))
      } else if (event.type === 'wave_complete') {
        // no-op (currentWave updated on next wave_start)
      } else if (event.type === 'file_complete') {
        const p = event.path ?? event.file_path ?? ''
        set((state) => ({
          codeGen: {
            ...state.codeGen,
            completedPaths: state.codeGen.completedPaths.includes(p)
              ? state.codeGen.completedPaths
              : [...state.codeGen.completedPaths, p],
          },
        }))
      } else if (event.type === 'tool_call') {
        set((state) => ({
          codeGen: {
            ...state.codeGen,
            reactSteps: [...state.codeGen.reactSteps, { tool: event.tool }],
          },
        }))
      } else if (event.type === 'react_step') {
        set((state) => ({
          codeGen: {
            ...state.codeGen,
            reactSteps: [...state.codeGen.reactSteps,
              { iteration: event.iteration, thought: event.thought }],
          },
        }))
      } else if (event.type === 'log' && event.line) {
        set((state) => ({
          codeGen: { ...state.codeGen, buildLogs: [...state.codeGen.buildLogs, event.line!] },
        }))
      } else if (event.type === 'complete') {
        // file_complete carried only paths; fetch full file contents now
        getGeneratedFiles().then((files) => {
          set((state) => ({
            codeGen: {
              ...state.codeGen,
              status: 'generated',
              generatedFiles: files.map((f) => ({
                file_path: f.file_path,
                file_type: f.file_type,
                content: f.content,
                layer: (f.layer ?? 'backend') as 'backend' | 'frontend',
              })),
            },
            statusMessage: null,
            _codegenAbort: null,
          }))
        })
      } else if (event.type === 'error') {
        set((state) => ({
          codeGen: { ...state.codeGen, status: 'error',
            error: event.content ?? event.message ?? 'Generation failed' },
          statusMessage: null,
          _codegenAbort: null,
        }))
      }
```

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc -b 2>&1 | tail -20`
Expected: PASS (no errors) — 모든 CodeGenState 초기화/접근이 신규 필드와 일치

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/store/sessionStore.ts
git commit -m "feat(frontend): rewrite generateCode handler for LangGraph events"
```

---

## Task 4: CodeGenPanel — wave 진행 + ReAct 타임라인

**Files:**
- Modify: `frontend/src/components/CodeGenPanel.tsx`

설계 참조: wave 병렬 진행 바, 계획 파일 대비 완료 표시, Reviewer ReAct(tool_call) 타임라인.

- [ ] **Step 1: CodeGenPanel 현재 구조 확인**

Run: `cd frontend && grep -n "codeGen\.\|status\|buildLogs\|generatedFiles\|generating" src/components/CodeGenPanel.tsx | head -30`
Expected: generating 상태일 때 렌더링하는 영역 파악.

- [ ] **Step 2: 진행 표시 블록 추가**

`CodeGenPanel.tsx`에서 `status === 'generating'`을 렌더하는 영역에, 다음 JSX 블록을 추가(기존 status 메시지 표시 근처). useSessionStore에서 codeGen을 이미 구독 중이라고 가정:

```tsx
{codeGen.status === 'generating' && (
  <div className="space-y-2 text-xs">
    {codeGen.currentNode && (
      <div className="text-[var(--md-sys-color-primary)]">
        ▶ {codeGen.currentNode}
        {codeGen.currentWave ? ` · wave ${codeGen.currentWave}` : ''}
      </div>
    )}
    {codeGen.plannedFiles.length > 0 && (
      <div className="text-[var(--md-sys-color-on-surface-variant)]">
        파일 {codeGen.completedPaths.length}/{codeGen.plannedFiles.length} 완료
      </div>
    )}
    {codeGen.reactSteps.length > 0 && (
      <div className="border-l-2 border-[var(--md-sys-color-outline)] pl-2">
        <div className="opacity-70">Reviewer:</div>
        {codeGen.reactSteps.slice(-5).map((s, i) => (
          <div key={i} className="opacity-80">
            {s.tool ? `🔧 ${s.tool}` : s.thought ? `💭 ${s.thought.slice(0, 80)}` : ''}
          </div>
        ))}
      </div>
    )}
  </div>
)}
```

**주의:** `codeGen`을 컴포넌트에서 구독하는 방식(예: `const { codeGen } = useSessionStore()` 또는 selector)을 Step 1에서 확인한 실제 코드에 맞춰 변수명을 사용. CSS 변수(`--md-sys-color-*`)는 `index.css`에 정의됨(프로젝트 테마).

- [ ] **Step 3: Type-check + build**

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: build 성공 (vue-tsc/tsc + vite build 통과)

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/components/CodeGenPanel.tsx
git commit -m "feat(frontend): show wave progress + reviewer ReAct timeline in CodeGenPanel"
```

---

## Task 5: 빌드 회귀 + 수동 확인 안내

**Files:** (없음 — 검증만)

- [ ] **Step 1: 전체 프론트 빌드**

Run: `cd frontend && npm run build 2>&1 | tail -15`
Expected: 타입 에러 0, 빌드 성공

- [ ] **Step 2: lint (있으면)**

Run: `cd frontend && npm run lint 2>&1 | tail -15`
Expected: 신규 코드에 lint 에러 없음 (기존 경고는 무방)

- [ ] **Step 3: 수동 확인 안내 (문서화)**

다음을 사용자에게 안내한다 (자동 불가):
1. `./start.sh`로 백엔드:8001 + 프론트:5173 기동
2. mockup 또는 텍스트로 spec + 확정 Vue 생성
3. 코드 생성 실행 → CodeGenPanel에서 node 진행/wave/Reviewer ReAct 타임라인이 보이는지
4. 완료 후 생성 파일 목록이 채워지는지(`/api/codegen/files`)

---

## Self-Review

**1. Spec coverage (설계 섹션 6 프론트 부분 대비):**
- SSEEvent 신규 타입(node/wave/tool/react/contract) → Task 1 ✅
- file_complete가 path만 싣는 변경 → complete 시 /files 조회 → Task 2·3 ✅
- generateCode 핸들러 신규 이벤트 → Task 3 ✅
- wave 진행 바 + ReAct 타임라인 UI → Task 4 ✅
- 파일별 토큰 스트리밍(file_token): 백엔드가 현재 file_token을 송출하지 않음(Plan 3는 node/file_complete 위주) → **이번 범위 제외**, 추후 백엔드가 on_chat_model_stream을 file_token으로 매핑하면 추가. 명시적 제외.

**2. Placeholder scan:** "TBD/TODO" 없음. Step 1/2의 "확인" 단계는 실제 코드 확인 지시(플레이스홀더 아님). 모든 코드 블록 실제 코드. ✅

**3. Type consistency:**
- SSEEvent 신규 필드(node/wave/file_count/path/tool/args/contract/files/iteration/thought)가 Task 3 핸들러 접근과 일치 ✅
- CodeGenState 신규 필드(currentNode/currentWave/reactSteps/plannedFiles/completedPaths)가 initialCodeGen(Task3 S1) + 핸들러 + 패널(Task4)에서 일치 ✅
- getGeneratedFiles 반환 형(file_path/file_type/content/layer)이 Task3 complete 핸들러의 매핑과 일치 ✅
- 백엔드 plan 이벤트가 `{type:'plan', files:[{file_path,file_type,wave}]}`(Plan2 planner node events) → Task3 plan 핸들러의 event.files 접근과 일치 ✅
- 백엔드 file_complete가 `{type:'file_complete', path, layer}`(Plan2 generate_file events) → Task3의 event.path 우선 접근과 일치 ✅

**알려진 리스크:**
- Plan 3의 `stream_codegen`은 노드 도메인 이벤트를 `on_chain_end` output에서 drain한다. wave_start/wave_complete/react_step은 현재 노드가 명시적으로 events에 넣지 않으면 프론트에 안 올 수 있다. Task 3 핸들러는 이 이벤트들이 와도/안 와도 안전하게 동작(없으면 단순히 표시 안 됨). 완전한 wave/react 시각화를 원하면 후속으로 nodes.py/react.py가 해당 이벤트를 events에 append하도록 보강 필요 — 이번 범위는 "이벤트가 오면 표시"까지.
- 프론트 자동 테스트 없음 → build 통과 + 수동 확인이 검증 기준(명시).
