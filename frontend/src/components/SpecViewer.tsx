import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useSessionStore } from '../store/sessionStore'
import StreamingText from './StreamingText'

export default function SpecViewer() {
  const specMarkdown = useSessionStore((s) => s.specMarkdown)
  const specVersion = useSessionStore((s) => s.specVersion)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const statusMessage = useSessionStore((s) => s.statusMessage)
  const rawInput = useSessionStore((s) => s.rawInput)

  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (specMarkdown && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight
    }
  }, [specMarkdown])

  return (
    <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/15 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-outline-variant/15 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold font-headline tracking-tight">Specification</h2>
          {specVersion > 0 && (
            <span className="bg-secondary-container text-on-secondary-container text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-tighter">
              v{specVersion}
            </span>
          )}
        </div>
      </div>

      {/* Original Requirements */}
      {rawInput && (
        <details className="group bg-surface-container-low px-6 py-3">
          <summary className="list-none cursor-pointer flex items-center justify-between text-xs font-semibold uppercase tracking-widest text-on-surface-variant">
            <span>Input Requirements</span>
            <span className="material-symbols-outlined group-open:rotate-180 transition-transform">
              expand_more
            </span>
          </summary>
          <pre className="mt-3 p-4 bg-surface-container text-xs text-secondary font-mono rounded-lg max-h-[160px] overflow-y-auto border border-outline-variant/10 leading-relaxed whitespace-pre-wrap">
            {rawInput}
          </pre>
        </details>
      )}

      {isGenerating && (
        <div className="px-5 py-3 bg-primary-fixed/30 border-b border-primary-fixed/50 text-sm text-primary flex items-center gap-2">
          <svg
            className="w-4 h-4 animate-spin text-primary"
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
        ref={contentRef}
        className="overflow-y-auto p-8 prose prose-slate max-w-none no-scrollbar"
        style={{ maxHeight: '70vh' }}
      >
        {specMarkdown ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{specMarkdown}</ReactMarkdown>
        ) : (
          !isGenerating && (
            <p className="text-outline text-sm">
              Your generated specification will appear here.
            </p>
          )
        )}
      </div>
    </div>
  )
}
