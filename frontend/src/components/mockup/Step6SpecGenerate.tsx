import { useSessionStore } from '../../store/sessionStore'

export default function Step6SpecGenerate() {
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const statusMessage = useSessionStore((s) => s.statusMessage)
  const specMarkdown = useSessionStore((s) => s.specMarkdown)

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-5">
        <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">description</span>
          Spec 생성
        </h3>

        {isGenerating && (
          <div className="flex items-center gap-3 text-sm text-on-surface-variant">
            <svg className="w-5 h-5 animate-spin text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span>{statusMessage ?? 'Spec 생성 중...'}</span>
          </div>
        )}

        {!isGenerating && specMarkdown && (
          <div className="flex items-center gap-2 px-4 py-3 bg-primary-fixed/30 rounded-lg">
            <span className="material-symbols-outlined text-primary">check_circle</span>
            <span className="text-sm font-bold text-on-surface">
              Spec 생성 완료! 좌측 Spec Viewer에서 확인하세요.
            </span>
          </div>
        )}

        {!isGenerating && !specMarkdown && (
          <p className="text-sm text-on-surface-variant">
            Spec이 아직 생성되지 않았습니다. 이전 단계에서 Spec 생성을 시작해주세요.
          </p>
        )}
      </div>
    </div>
  )
}
