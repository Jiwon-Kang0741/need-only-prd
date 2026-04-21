import { useSessionStore } from '../../store/sessionStore'

export default function Step3Annotate() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const aiAnnotate = useSessionStore((s) => s.mockupAiAnnotate)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const hasResult = mockupState?.annotationMarkdown !== null

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-5">
        <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">comment</span>
          UI 주석 자동 삽입
        </h3>
        <p className="text-sm text-on-surface-variant">
          생성된 Vue Mockup 코드를 분석하여 각 UI 요소에 대한 주석을 자동으로 생성합니다.
        </p>

        {error && (
          <div className="text-sm text-error bg-error-container/30 px-4 py-2 rounded-lg">
            {error}
          </div>
        )}

        {!hasResult && (
          <button
            type="button"
            onClick={aiAnnotate}
            disabled={loading}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {loading ? (
              <>
                <svg className="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                주석 생성 중...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined">auto_fix_high</span>
                UI 주석 자동 삽입
              </>
            )}
          </button>
        )}
      </div>

      {hasResult && mockupState?.annotationMarkdown && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-4">
          <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-tertiary">check_circle</span>
            주석 결과
          </h3>
          <pre className="bg-inverse-surface text-inverse-on-surface rounded-lg p-4 text-xs overflow-x-auto max-h-[400px] overflow-y-auto leading-relaxed whitespace-pre-wrap">
            {mockupState.annotationMarkdown}
          </pre>

          <button
            type="button"
            onClick={() => goToStep(4)}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2"
          >
            다음: 인터뷰
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      )}
    </div>
  )
}
