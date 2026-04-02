import ReactMarkdown from 'react-markdown'
import { useSessionStore } from '../store/sessionStore'

export default function CompareView() {
  const rawInput = useSessionStore((s) => s.rawInput)
  const specMarkdown = useSessionStore((s) => s.specMarkdown)

  return (
    <div className="bg-white rounded-lg border shadow-sm flex flex-col">
      <div className="px-5 py-3 border-b">
        <h2 className="text-lg font-semibold text-gray-800">Compare</h2>
      </div>
      <div className="grid grid-cols-2 divide-x overflow-hidden" style={{ minHeight: '60vh' }}>
        <div className="flex flex-col">
          <div className="px-4 py-2 bg-gray-50 border-b text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Original Text
          </div>
          <div
            className="overflow-y-auto p-4 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed"
            style={{ maxHeight: '70vh' }}
          >
            {rawInput ?? <span className="text-gray-400 italic">No original text available.</span>}
          </div>
        </div>
        <div className="flex flex-col">
          <div className="px-4 py-2 bg-gray-50 border-b text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Generated Spec
          </div>
          <div
            className="overflow-y-auto p-4 prose prose-sm max-w-none"
            style={{ maxHeight: '70vh' }}
          >
            {specMarkdown ? (
              <ReactMarkdown>{specMarkdown}</ReactMarkdown>
            ) : (
              <p className="text-gray-400 text-sm italic">No spec generated yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
