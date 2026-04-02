import ReactMarkdown from 'react-markdown'
import { useSessionStore } from '../store/sessionStore'
import StreamingText from './StreamingText'

export default function SpecViewer() {
  const specMarkdown = useSessionStore((s) => s.specMarkdown)
  const specVersion = useSessionStore((s) => s.specVersion)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const statusMessage = useSessionStore((s) => s.statusMessage)

  return (
    <div className="bg-white rounded-lg border shadow-sm flex flex-col">
      <div className="flex items-center justify-between px-5 py-3 border-b">
        <h2 className="text-lg font-semibold text-gray-800">Specification</h2>
        {specVersion > 0 && (
          <span className="text-xs font-medium bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
            v{specVersion}
          </span>
        )}
      </div>

      {isGenerating && (
        <div className="px-5 py-2 bg-blue-50 border-b text-sm text-blue-700 flex items-center gap-2">
          <svg
            className="w-4 h-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"
            />
          </svg>
          <StreamingText
            text={statusMessage ?? 'Analyzing requirements...'}
            isStreaming={isGenerating}
          />
        </div>
      )}

      <div
        className="overflow-y-auto p-5 prose prose-sm max-w-none"
        style={{ maxHeight: '70vh' }}
      >
        {specMarkdown ? (
          <ReactMarkdown>{specMarkdown}</ReactMarkdown>
        ) : (
          !isGenerating && (
            <p className="text-gray-400 text-sm">
              Your generated specification will appear here.
            </p>
          )
        )}
      </div>
    </div>
  )
}
