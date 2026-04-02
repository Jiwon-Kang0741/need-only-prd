import { useSession } from './hooks/useSession'
import { useSessionStore } from './store/sessionStore'
import Layout from './components/Layout'
import InputPanel from './components/InputPanel'
import SpecViewer from './components/SpecViewer'
import ChatPanel from './components/ChatPanel'
import CompareView from './components/CompareView'
import CoverageScore from './components/CoverageScore'
import ExportButton from './components/ExportButton'

function App() {
  useSession()
  const specMarkdown = useSessionStore((s) => s.specMarkdown)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const showCompare = useSessionStore((s) => s.showCompare)
  const toggleCompare = useSessionStore((s) => s.toggleCompare)
  const reset = useSessionStore((s) => s.reset)

  const showSpec = specMarkdown !== null || isGenerating

  return (
    <Layout onNewSession={reset}>
      {!showSpec ? (
        <InputPanel />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 flex flex-col gap-3">
            {showCompare ? <CompareView /> : <SpecViewer />}
            <div className="flex items-center gap-3 flex-wrap">
              <button
                onClick={toggleCompare}
                className="px-3 py-1.5 rounded-md text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
              >
                {showCompare ? 'Hide Compare' : 'Compare View'}
              </button>
              <CoverageScore />
              <ExportButton />
            </div>
          </div>
          <div className="lg:col-span-1">
            <ChatPanel />
          </div>
        </div>
      )}
    </Layout>
  )
}

export default App
