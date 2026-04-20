import { useSession } from './hooks/useSession'
import { useSessionStore } from './store/sessionStore'
import Layout from './components/Layout'
import SpecModeSelector from './components/SpecModeSelector'
import SpecViewer from './components/SpecViewer'
import ChatPanel from './components/ChatPanel'
import CompareView from './components/CompareView'
import CoverageScore from './components/CoverageScore'
import ExportButton from './components/ExportButton'
import CodeGenPanel from './components/CodeGenPanel'
import StreamingText from './components/StreamingText'

function App() {
  useSession()
  const specMarkdown = useSessionStore((s) => s.specMarkdown)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const statusMessage = useSessionStore((s) => s.statusMessage)
  const showCompare = useSessionStore((s) => s.showCompare)
  const toggleCompare = useSessionStore((s) => s.toggleCompare)
  const reset = useSessionStore((s) => s.reset)

  const showSpec = specMarkdown !== null
  const showOverlay = isGenerating && !specMarkdown

  return (
    <Layout onNewSession={reset}>
      {/* Full-screen generating overlay */}
      {showOverlay && (
        <div className="fixed inset-0 z-40 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(6px)' }}>
          <div className="rounded-2xl shadow-2xl px-10 py-8 flex flex-col items-center gap-5 max-w-sm mx-4" style={{ background: '#1a1a1a', border: '1px solid #2a2a2a' }}>
            <div className="w-14 h-14 rounded-xl flex items-center justify-center" style={{ background: 'rgba(244,130,31,0.15)' }}>
              <svg
                className="w-8 h-8 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                style={{ color: '#f4821f' }}
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-bold font-headline text-white mb-1">Generating Specification</h3>
              <p className="text-sm" style={{ color: '#888888' }}>
                <StreamingText
                  text={statusMessage ?? 'Analyzing requirements...'}
                  isStreaming={true}
                />
              </p>
            </div>
            <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: '#2a2a2a' }}>
              <div className="h-full rounded-full animate-pulse" style={{ width: '60%', background: '#f4821f' }} />
            </div>
          </div>
        </div>
      )}

      {!showSpec && !showOverlay ? (
        <SpecModeSelector />
      ) : showSpec ? (
        <div className="max-w-[1600px] mx-auto p-6 grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          {/* Left: Spec + Chat (Refine) */}
          <div className="flex flex-col gap-3">
            {showCompare ? <CompareView /> : <SpecViewer />}
            <div className="flex items-center gap-3 flex-wrap">
              <button
                onClick={toggleCompare}
                className="bg-surface-container-high hover:bg-surface-variant text-on-surface px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 transition-all"
              >
                <span className="material-symbols-outlined text-[20px]">compare</span>
                {showCompare ? 'Hide Compare' : 'Compare View'}
              </button>
              <CoverageScore />
              <ExportButton />
            </div>
            <ChatPanel />
          </div>
          {/* Right: Code Generation */}
          <div className="sticky top-24">
            {!isGenerating && specMarkdown && (
              <CodeGenPanel />
            )}
          </div>
        </div>
      ) : null}
    </Layout>
  )
}

export default App
