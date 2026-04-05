import { useState } from 'react'
import { useSessionStore } from '../store/sessionStore'
import { downloadCode } from '../api/client'
import FileViewer from './FileViewer'

export default function CodeGenPanel() {
  const codeGen = useSessionStore((s) => s.codeGen)
  const generateCode = useSessionStore((s) => s.generateCode)
  const deployAndRun = useSessionStore((s) => s.deployAndRun)
  const stopContainers = useSessionStore((s) => s.stopContainers)
  const statusMessage = useSessionStore((s) => s.statusMessage)

  const { status, plan, generatedFiles, buildLogs, error, ports } = codeGen

  const [showFiles, setShowFiles] = useState(false)
  const [showLogs, setShowLogs] = useState(false)

  // Idle — start button
  if (status === 'idle') {
    return (
      <div className="bg-inverse-surface text-inverse-on-surface rounded-2xl shadow-xl overflow-hidden p-8">
        <h3 className="text-xl font-bold font-headline mb-3">Code Generation</h3>
        <p className="text-sm text-inverse-on-surface/60 mb-6">
          Multi-agent system generates Spring Boot + Vue3 code from the specification.
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
      <div className="bg-inverse-surface text-inverse-on-surface rounded-2xl shadow-xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-5 flex justify-between items-center bg-black/20 border-b border-white/10">
          <div className="flex items-center">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
              <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
              <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
            </div>
            <div className="h-4 w-px bg-white/10 mx-2" />
            <span className="text-xs font-mono text-white/60">Generating Code</span>
          </div>
        </div>

        {/* Status */}
        <div className="px-5 py-3 flex items-center gap-2 text-sm text-inverse-on-surface/80">
          <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
          {statusMessage ?? 'Working...'}
        </div>

        {/* Plan preview */}
        {plan && (
          <div className="px-5 py-2 text-xs text-white/50">
            {plan.files.length} files planned for <span className="font-mono font-semibold">{plan.screen_code}</span>
          </div>
        )}

        {/* Generated files so far */}
        {generatedFiles.length > 0 && (
          <div className="px-5 pb-4">
            <div className="text-xs text-white/50 font-medium mb-2">{generatedFiles.length} files generated</div>
            {generatedFiles.map((f, i) => (
              <details key={i} className="border-b border-white/10 last:border-b-0">
                <summary className="px-3 py-2 text-xs cursor-pointer hover:bg-white/5 flex items-center gap-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${f.layer === 'backend' ? 'bg-emerald-900/50 text-emerald-300' : 'bg-blue-900/50 text-blue-300'}`}>
                    {f.layer}
                  </span>
                  <span className="font-mono text-white/80 truncate">{f.file_path}</span>
                </summary>
                <pre className="bg-black/40 text-gray-100 text-[11px] p-3 font-mono overflow-x-auto max-h-48">
                  {f.content}
                </pre>
              </details>
            ))}
          </div>
        )}

        {/* Build logs */}
        {buildLogs.length > 0 && (
          <div className="mx-5 mb-4 rounded-lg p-3 bg-black/30 max-h-32 overflow-auto">
            {buildLogs.map((log, i) => (
              <div key={i} className="text-xs text-white/50 font-mono">{log}</div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Generated / Building / Running
  if (status === 'generated' || status === 'building' || status === 'running') {
    return (
      <div className="bg-inverse-surface text-inverse-on-surface rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="p-5 flex items-center justify-between bg-black/20 border-b border-white/10">
          <div className="flex items-center">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
              <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
              <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
            </div>
            <div className="h-4 w-px bg-white/10 mx-2" />
            <span className="text-xs font-mono text-white/60">Generated Code &middot; {generatedFiles.length} files</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowFiles(!showFiles)} className="text-white/60 hover:text-white transition-colors text-xs flex items-center gap-1">
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>folder_open</span>
              {showFiles ? 'Hide Files' : 'View Files'}
            </button>
            <button onClick={downloadCode} className="bg-primary px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider text-white hover:opacity-90">
              Download ZIP
            </button>
            <button onClick={generateCode} className="text-white/60 hover:text-white transition-colors text-xs flex items-center gap-1">
              <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>refresh</span>
              Regenerate
            </button>
          </div>
        </div>

        {/* Deploy & Run */}
        <div className="p-5 border-t border-white/10">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-bold text-white/80">Deploy & Run (CPMS Skeleton)</h4>
            <div className="flex gap-2">
              {status === 'generated' && (
                <button onClick={deployAndRun} className="gradient-button text-on-primary px-4 py-1.5 rounded-xl font-bold text-xs hover:opacity-90 transition-all">
                  Deploy & Run
                </button>
              )}
              {status === 'building' && (
                <span className="flex items-center gap-2 text-sm text-inverse-on-surface/80">
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
                <span className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg bg-white/10 text-white/60">
                  DB :{ports.db}
                </span>
              )}
            </div>
          )}

          {buildLogs.length > 0 && (
            <div>
              <button onClick={() => setShowLogs(!showLogs)} className="text-xs text-white/40 hover:text-white/60 cursor-pointer mb-1">
                {showLogs ? 'Hide' : 'Show'} Logs ({buildLogs.length})
              </button>
              {showLogs && (
                <div className="rounded-lg p-3 bg-black/30 max-h-48 overflow-auto">
                  {buildLogs.map((log, i) => (
                    <div key={i} className="text-xs text-white/50 font-mono">{log}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {status === 'generated' && buildLogs.length === 0 && (
            <p className="text-xs text-white/50">Deploy to CPMS skeleton project and run in Docker.</p>
          )}
        </div>

        {/* CPMS info banner */}
        <div className="bg-tertiary/10 border border-tertiary/20 rounded-lg p-4 mx-5 mb-5">
          <p className="text-sm font-bold text-white flex items-center gap-1.5">
            <span className="material-symbols-outlined text-tertiary" style={{ fontSize: '18px' }}>auto_awesome</span>
            CPMS Project Integration
          </p>
          <p className="text-xs text-white/50 mt-1">
            Download ZIP to integrate into your CPMS project, or Deploy & Run to preview.
          </p>
        </div>

        {/* Footer with file chips */}
        {generatedFiles.length > 0 && !showFiles && (
          <div className="p-5 bg-black/20 border-t border-white/10">
            <div className="grid grid-cols-3 gap-2">
              {generatedFiles.slice(0, 9).map((f, i) => (
                <div key={i} onClick={() => setShowFiles(true)} className="bg-white/5 p-2 rounded-lg border border-white/5 hover:border-white/10 transition-colors cursor-pointer">
                  <div className="text-[9px] font-bold text-white/40 mb-1">{f.layer}</div>
                  <div className="text-[10px] font-mono text-white/80 truncate">{f.file_path.split('/').pop()}</div>
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
      <div className="bg-inverse-surface text-inverse-on-surface rounded-2xl shadow-xl overflow-hidden p-6">
        <h3 className="text-lg font-bold font-headline text-error mb-2">Error</h3>
        <p className="text-sm text-error/80 mb-4 whitespace-pre-wrap">{error}</p>
        {buildLogs.length > 0 && (
          <div className="rounded-lg p-3 bg-black/30 max-h-32 overflow-auto mb-4">
            {buildLogs.map((log, i) => (
              <div key={i} className="text-xs text-white/50 font-mono">{log}</div>
            ))}
          </div>
        )}
        <div className="flex gap-2">
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
          <button onClick={generateCode} className="bg-white/10 text-white/80 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/15 transition-all">
            Regenerate Code
          </button>
        </div>
      </div>
    )
  }

  return null
}
