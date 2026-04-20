import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useSessionStore } from '../store/sessionStore'

export default function CompareView() {
  const rawInput = useSessionStore((s) => s.rawInput)
  const specMarkdown = useSessionStore((s) => s.specMarkdown)

  return (
    <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/15 overflow-hidden flex flex-col">
      <div className="p-6 border-b border-outline-variant/15">
        <h2 className="text-xl font-bold font-headline tracking-tight">Compare</h2>
      </div>
      <div className="grid grid-cols-2 divide-x divide-outline-variant/15 overflow-hidden" style={{ minHeight: '60vh' }}>
        <div className="flex flex-col">
          <div className="px-4 py-2 bg-surface-container-low border-b border-outline-variant/15 text-xs font-bold text-on-surface-variant uppercase tracking-widest">
            Original Text
          </div>
          <div className="overflow-y-auto p-6 text-sm text-on-surface-variant whitespace-pre-wrap leading-relaxed no-scrollbar">
            {rawInput ?? <span className="text-outline italic">No original text available.</span>}
          </div>
        </div>
        <div className="flex flex-col">
          <div className="px-4 py-2 bg-surface-container-low border-b border-outline-variant/15 text-xs font-bold text-on-surface-variant uppercase tracking-widest">
            Generated Spec
          </div>
          <div className="overflow-y-auto p-6 prose prose-sm prose-invert max-w-none no-scrollbar bg-zinc-900 text-white prose-headings:text-white prose-p:text-white prose-li:text-white prose-strong:text-white prose-a:text-sky-300 prose-code:text-amber-200 prose-pre:bg-zinc-950">
            {specMarkdown ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{specMarkdown}</ReactMarkdown>
            ) : (
              <p className="text-zinc-400 text-sm italic">아직 생성된 스펙이 없습니다.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
