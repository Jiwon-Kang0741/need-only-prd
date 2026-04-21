import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useSessionStore } from '../../store/sessionStore'

export default function Step6SpecGenerate() {
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const statusMessage = useSessionStore((s) => s.statusMessage)
  const specMarkdown = useSessionStore((s) => s.specMarkdown)
  const mockupError = useSessionStore((s) => s.mockupError)
  const generateSpec = useSessionStore((s) => s.mockupGenerateSpec)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)
  const generateCode = useSessionStore((s) => s.generateCode)

  function handleGenerateCode() {
    goToStep(7)
    generateCode()
  }

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-5">
        <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">description</span>
          Spec 생성
        </h3>

        {/* 생성 중 */}
        {isGenerating && (
          <div className="flex items-center gap-3 text-sm text-on-surface-variant">
            <svg className="w-5 h-5 animate-spin text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span>{statusMessage ?? 'Spec 생성 중...'}</span>
          </div>
        )}

        {/* 에러 */}
        {!isGenerating && mockupError && (
          <div
            className="rounded-lg px-4 py-3 text-sm space-y-3"
            style={{ background: 'rgba(255,107,107,0.1)', border: '1px solid rgba(255,107,107,0.25)', color: '#ff6b6b' }}
          >
            <div className="flex items-start gap-2">
              <span className="material-symbols-outlined text-[18px] flex-shrink-0 mt-0.5">error</span>
              <div>
                <p className="font-semibold mb-1">Spec 생성 실패</p>
                <p className="text-xs opacity-80 break-all">{mockupError}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={generateSpec}
              disabled={isGenerating}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all"
              style={{ background: 'rgba(255,107,107,0.15)', border: '1px solid rgba(255,107,107,0.3)', color: '#ff6b6b', cursor: 'pointer' }}
            >
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              다시 시도
            </button>
          </div>
        )}

        {/* 미생성 (에러 없음) */}
        {!isGenerating && !specMarkdown && !mockupError && (
          <div className="space-y-4">
            <p className="text-sm text-on-surface-variant">
              인터뷰 결과를 바탕으로 최종 Spec을 생성합니다. 아래 버튼을 클릭하세요.
            </p>
            <button
              type="button"
              onClick={generateSpec}
              disabled={isGenerating}
              className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined">description</span>
              최종 Spec 생성 (스트리밍)
            </button>
          </div>
        )}
      </div>

      {/* 생성된 Spec 인라인 표시 */}
      {specMarkdown && (
        <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
          {/* 헤더 */}
          <div
            className="flex items-center justify-between px-6 py-4"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
          >
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[18px]">
                {isGenerating ? 'pending' : 'check_circle'}
              </span>
              <span className="text-sm font-bold text-on-surface">
                {isGenerating ? 'Spec 스트리밍 중...' : 'Spec 생성 완료'}
              </span>
            </div>
            {!isGenerating && (
              <button
                type="button"
                onClick={generateSpec}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                style={{ background: 'rgba(244,130,31,0.1)', color: '#f4821f', border: '1px solid rgba(244,130,31,0.2)' }}
              >
                <span className="material-symbols-outlined text-[14px]">refresh</span>
                재생성
              </button>
            )}
          </div>

          {/* Markdown 본문 */}
          <div
            className="overflow-y-auto p-6 max-w-none no-scrollbar bg-zinc-900 text-white prose prose-invert prose-headings:text-white prose-p:text-white prose-li:text-white prose-strong:text-white prose-a:text-sky-300 prose-code:text-amber-200 prose-pre:bg-zinc-950 prose-pre:text-zinc-100 prose-th:text-white prose-td:text-zinc-200"
            style={{ maxHeight: 'calc(100vh - 420px)', minHeight: '200px' }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {specMarkdown}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* Generate Code 버튼 — spec 완료 후 표시 */}
      {!isGenerating && specMarkdown && (
        <div
          className="rounded-xl p-5 flex items-center justify-between gap-4"
          style={{ background: 'rgba(244,130,31,0.06)', border: '1px solid rgba(244,130,31,0.2)' }}
        >
          <div>
            <p className="text-sm font-bold text-white">다음 단계: Code 생성</p>
            <p className="text-xs mt-0.5" style={{ color: '#888' }}>
              Spec을 바탕으로 Spring Boot + Vue3 소스 코드를 자동 생성합니다.
            </p>
          </div>
          <button
            type="button"
            onClick={handleGenerateCode}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2 flex-shrink-0"
          >
            <span className="material-symbols-outlined">auto_awesome</span>
            Generate Code
          </button>
        </div>
      )}
    </div>
  )
}
