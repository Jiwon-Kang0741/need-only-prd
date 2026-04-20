import { useEffect, useRef, useState } from 'react'
import { useSessionStore } from '../store/sessionStore'
import { downloadCode } from '../api/client'
import FileViewer from './FileViewer'

export default function CodeGenPanel() {
  const codeGen = useSessionStore((s) => s.codeGen)
  const generateCode = useSessionStore((s) => s.generateCode)
  const stopGeneration = useSessionStore((s) => s.stopGeneration)
  const deployAndRun = useSessionStore((s) => s.deployAndRun)
  const stopContainers = useSessionStore((s) => s.stopContainers)
  const deleteSource = useSessionStore((s) => s.deleteSource)
  const statusMessage = useSessionStore((s) => s.statusMessage)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  const { status, plan, generatedFiles, buildLogs, error, ports } = codeGen

  const [showFiles, setShowFiles] = useState(false)
  const [showLogs, setShowLogs] = useState(false)
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (status === 'building' || showLogs) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [buildLogs, status, showLogs])

  // Idle — start button
  if (status === 'idle') {
    return (
      <div className="bg-white text-neutral-900 rounded-2xl shadow-xl border border-neutral-200 overflow-hidden p-8">
        <h3 className="text-xl font-bold font-headline mb-3">Code Generation</h3>
        <p className="text-sm text-neutral-600 mb-6">
          멀티 에이전트가 스펙을 바탕으로 Spring Boot + Vue3 코드를 생성합니다.
        </p>
        <button onClick={generateCode} className="gradient-button text-on-primary px-5 py-2.5 rounded-xl font-bold text-sm flex items-center gap-2 hover:opacity-90 transition-all">
          <span className="material-symbols-outlined">auto_awesome</span>
          Generate Code
        </button>
      </div>
    )
  }

  // Generating — show agent progress
  if (status === 'generating') {
    return (
      <div className="bg-white text-neutral-900 rounded-2xl shadow-xl border border-neutral-200 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-5 flex justify-between items-center bg-neutral-100 border-b border-neutral-200">
          <div className="flex items-center">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
              <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
              <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
            </div>
            <div className="h-4 w-px bg-neutral-300 mx-2" />
            <span className="text-xs font-mono text-neutral-600">Generating Code</span>
          </div>
          <button
            onClick={stopGeneration}
            className="bg-error/90 hover:bg-error text-white px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors"
          >
            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>stop_circle</span>
            Stop
          </button>
        </div>

        {/* Status */}
        <div className="px-5 py-3 flex items-center gap-2 text-sm text-neutral-800">
          <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
          {statusMessage ?? 'Working...'}
        </div>

        {/* Plan preview */}
        {plan && (
          <div className="px-5 py-2 text-xs text-neutral-600">
            {plan.files.length}개 파일 예정 — <span className="font-mono font-semibold text-neutral-900">{plan.screen_code}</span>
          </div>
        )}

        {/* Generated files so far */}
        {generatedFiles.length > 0 && (
          <div className="px-5 pb-4">
            <div className="text-xs text-neutral-700 font-medium mb-2">{generatedFiles.length}개 파일 생성됨</div>
            {generatedFiles.map((f, i) => (
              <details key={i} className="border-b border-neutral-200 last:border-b-0">
                <summary className="px-3 py-2 text-xs cursor-pointer hover:bg-neutral-50 flex items-center gap-2 text-neutral-900">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${f.layer === 'backend' ? 'bg-emerald-100 text-emerald-900' : 'bg-sky-100 text-sky-900'}`}>
                    {f.layer}
                  </span>
                  <span className="font-mono truncate">{f.file_path}</span>
                </summary>
                <pre className="bg-neutral-100 text-neutral-900 text-[11px] p-3 font-mono overflow-x-auto max-h-48 border-t border-neutral-200">
                  {f.content}
                </pre>
              </details>
            ))}
          </div>
        )}

        {/* Build logs */}
        {buildLogs.length > 0 && (
          <div className="mx-5 mb-4 rounded-lg p-3 bg-neutral-100 max-h-32 overflow-auto border border-neutral-200">
            {buildLogs.map((log, i) => (
              <div key={i} className="text-xs text-neutral-800 font-mono">{log}</div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Generated / Building / Running
  if (status === 'generated' || status === 'building' || status === 'running') {
    return (
      <div className="bg-white text-neutral-900 rounded-2xl shadow-xl border border-neutral-200 overflow-hidden">
        {/* Header */}
        <div className="p-5 flex items-center justify-between bg-neutral-100 border-b border-neutral-200">
          <div className="flex items-center">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
              <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
              <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
            </div>
            <div className="h-4 w-px bg-neutral-300 mx-2" />
            <span className="text-xs font-mono text-neutral-700">Generated Code · {generatedFiles.length} files</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowFiles(!showFiles)} className="text-neutral-600 hover:text-neutral-900 transition-colors text-xs flex items-center gap-1">
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>folder_open</span>
              {showFiles ? 'Hide Files' : 'View Files'}
            </button>
            <button onClick={downloadCode} className="bg-primary px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider text-white hover:opacity-90">
              Download ZIP
            </button>
            <button onClick={generateCode} className="text-neutral-600 hover:text-neutral-900 transition-colors text-xs flex items-center gap-1">
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>refresh</span>
              Regenerate
            </button>
            {deleteConfirm ? (
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-red-600">삭제?</span>
                <button
                  onClick={() => { deleteSource(); setDeleteConfirm(false) }}
                  className="bg-red-600 hover:bg-red-500 text-white px-2 py-1 rounded text-[10px] font-bold transition-colors"
                >
                  확인
                </button>
                <button
                  onClick={() => setDeleteConfirm(false)}
                  className="bg-neutral-200 hover:bg-neutral-300 text-neutral-800 px-2 py-1 rounded text-[10px] transition-colors"
                >
                  취소
                </button>
              </div>
            ) : (
              <button
                onClick={() => setDeleteConfirm(true)}
                className="text-red-600/80 hover:text-red-600 transition-colors text-xs flex items-center gap-1"
                title="생성된 소스 파일 전체 삭제"
              >
                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>delete_sweep</span>
                Delete Source
              </button>
            )}
          </div>
        </div>

        {/* Deploy & Run */}
        <div className="p-5 border-t border-neutral-200">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-bold text-neutral-900">Deploy & Run (CPMS Skeleton)</h4>
            <div className="flex gap-2">
              {status === 'generated' && (
                <button onClick={deployAndRun} className="gradient-button text-on-primary px-4 py-1.5 rounded-xl font-bold text-xs hover:opacity-90 transition-all">
                  Deploy & Run
                </button>
              )}
              {status === 'building' && (
                <span className="flex items-center gap-2 text-sm text-neutral-800">
                  <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
                  {statusMessage ?? 'Building...'}
                </span>
              )}
              {status === 'running' && (
                <button onClick={stopContainers} className="bg-error px-4 py-1.5 rounded-xl text-white text-xs font-bold hover:opacity-90 transition-all">
                  Stop
                </button>
              )}
            </div>
          </div>

          {status === 'running' && ports && (
            <div className="flex flex-wrap gap-3 mb-3">
              {ports.frontend && (
                <a href={`http://localhost:${ports.frontend}`} target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg bg-primary text-white">
                  Frontend :{ports.frontend}
                </a>
              )}
              {ports.backend && (
                <a href={`http://localhost:${ports.backend}`} target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg bg-emerald-600 text-white">
                  Backend API :{ports.backend}
                </a>
              )}
              {ports.db && (
                <span className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg bg-neutral-200 text-neutral-800">
                  DB :{ports.db}
                </span>
              )}
            </div>
          )}

          {status === 'building' && buildLogs.length > 0 && (
            <div className="rounded-lg p-3 bg-neutral-100 max-h-96 overflow-auto border border-neutral-200">
              {buildLogs.map((log, i) => (
                <div key={i} className={`text-xs font-mono ${log.includes('[ERROR]') ? 'text-red-700' : log.includes('[INFO]') || log.includes('[FIX]') ? 'text-emerald-800' : log.includes('[WARN]') ? 'text-amber-800' : 'text-neutral-700'}`}>
                  {log}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          )}

          {status !== 'building' && buildLogs.length > 0 && (
            <div>
              <button onClick={() => setShowLogs(!showLogs)} className="text-xs text-neutral-500 hover:text-neutral-800 cursor-pointer mb-1">
                {showLogs ? 'Hide' : 'Show'} Logs ({buildLogs.length})
              </button>
              {showLogs && (
                <div className="rounded-lg p-3 bg-neutral-100 max-h-64 overflow-auto border border-neutral-200">
                  {buildLogs.map((log, i) => (
                    <div key={i} className={`text-xs font-mono ${log.includes('[ERROR]') ? 'text-red-700' : log.includes('[INFO]') || log.includes('[FIX]') ? 'text-emerald-800' : log.includes('[WARN]') ? 'text-amber-800' : 'text-neutral-700'}`}>
                      {log}
                    </div>
                  ))}
                  <div ref={logEndRef} />
                </div>
              )}
            </div>
          )}

          {status === 'generated' && buildLogs.length === 0 && (
            <p className="text-xs text-neutral-600">CPMS 스켈레톤에 배포 후 Docker에서 실행합니다.</p>
          )}
        </div>

        {/* CPMS info banner */}
        <div className="bg-tertiary/10 border border-tertiary/20 rounded-lg p-4 mx-5 mb-5">
          <p className="text-sm font-bold text-neutral-900 flex items-center gap-1.5">
            <span className="material-symbols-outlined text-tertiary" style={{ fontSize: '18px' }}>auto_awesome</span>
            CPMS Project Integration
          </p>
          <p className="text-xs text-neutral-600 mt-1">
            ZIP으로 내려받아 CPMS 프로젝트에 반영하거나, Deploy & Run으로 미리보기 하세요.
          </p>
        </div>

        {/* Footer with file chips */}
        {generatedFiles.length > 0 && !showFiles && (
          <div className="p-5 bg-neutral-50 border-t border-neutral-200">
            <div className="grid grid-cols-3 gap-2">
              {generatedFiles.slice(0, 9).map((f, i) => (
                <div key={i} onClick={() => setShowFiles(true)} className="bg-white p-2 rounded-lg border border-neutral-200 hover:border-neutral-400 transition-colors cursor-pointer">
                  <div className="text-[9px] font-bold text-neutral-500 mb-1">{f.layer}</div>
                  <div className="text-[10px] font-mono text-neutral-900 truncate">{f.file_path.split('/').pop()}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {showFiles && <FileViewer files={generatedFiles} />}
      </div>
    )
  }

  // Error
  if (status === 'error') {
    const hasFiles = generatedFiles.length > 0
    return (
      <div className="bg-white text-neutral-900 rounded-2xl shadow-xl border border-neutral-200 overflow-hidden p-6">
        <h3 className="text-lg font-bold font-headline text-error mb-2">Error</h3>
        <p className="text-sm text-red-800 mb-4 whitespace-pre-wrap">{error}</p>
        {buildLogs.length > 0 && (
          <div className="rounded-lg p-3 bg-neutral-100 max-h-64 overflow-auto mb-4 border border-neutral-200">
            {buildLogs.map((log, i) => (
              <div key={i} className={`text-xs font-mono ${log.includes('[ERROR]') ? 'text-red-700' : log.includes('[INFO]') || log.includes('[FIX]') ? 'text-emerald-800' : log.includes('[WARN]') ? 'text-amber-800' : 'text-neutral-700'}`}>
                {log}
              </div>
            ))}
          </div>
        )}
        <div className="flex gap-2 flex-wrap">
          {hasFiles && (
            <>
              <button onClick={deployAndRun} className="gradient-button text-on-primary px-4 py-2 rounded-xl font-bold text-sm hover:opacity-90 transition-all">
                Retry Deploy
              </button>
              <button onClick={downloadCode} className="bg-primary px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider text-white hover:opacity-90">
                Download ZIP
              </button>
            </>
          )}
          <button onClick={generateCode} className="bg-neutral-200 text-neutral-900 px-4 py-2 rounded-xl text-sm font-bold hover:bg-neutral-300 transition-all">
            Regenerate Code
          </button>
          {deleteConfirm ? (
            <div className="flex items-center gap-1">
              <span className="text-xs text-red-600">삭제?</span>
              <button
                onClick={() => { deleteSource(); setDeleteConfirm(false) }}
                className="bg-red-600 hover:bg-red-500 text-white px-3 py-1.5 rounded-xl text-sm font-bold transition-colors"
              >
                확인
              </button>
              <button
                onClick={() => setDeleteConfirm(false)}
                className="bg-neutral-200 text-neutral-800 px-3 py-1.5 rounded-xl text-sm transition-colors"
              >
                취소
              </button>
            </div>
          ) : (
            <button
              onClick={() => setDeleteConfirm(true)}
              className="bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-1.5 transition-all"
            >
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>delete_sweep</span>
              Delete Source
            </button>
          )}
        </div>
      </div>
    )
  }

  return null
}
