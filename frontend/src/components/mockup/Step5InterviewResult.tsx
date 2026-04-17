import { useSessionStore } from '../../store/sessionStore'

export default function Step5InterviewResult() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const generateSpec = useSessionStore((s) => s.mockupGenerateSpec)

  const noteMd = mockupState?.interviewNoteMd ?? null

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-5">
        <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">summarize</span>
          인터뷰 결과
        </h3>

        {noteMd ? (
          <pre className="bg-inverse-surface text-inverse-on-surface rounded-lg p-4 text-xs overflow-x-auto max-h-[500px] overflow-y-auto leading-relaxed whitespace-pre-wrap">
            {noteMd}
          </pre>
        ) : (
          <p className="text-sm text-on-surface-variant">인터뷰 결과가 없습니다.</p>
        )}

        {noteMd && (
          <button
            type="button"
            onClick={generateSpec}
            disabled={loading || isGenerating}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {isGenerating ? (
              <>
                <svg className="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Spec 생성 중...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined">description</span>
                최종 Spec 생성 (스트리밍)
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}
