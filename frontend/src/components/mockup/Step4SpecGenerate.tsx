import { useSessionStore } from '../../store/sessionStore'

export default function Step4SpecGenerate() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const statusMessage = useSessionStore((s) => s.statusMessage)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)
  const generateSpec = useSessionStore((s) => s.mockupGenerateSpec)

  const briefOk = !!mockupState?.briefMd
  const mockupOk = !!mockupState?.mockupVue
  const notesOk = !!mockupState?.interviewNotesMd
  const canGenerate = briefOk && mockupOk && notesOk && !isGenerating

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold font-headline text-on-surface mb-1">④ Spec 생성</h2>
        <p className="text-sm text-on-surface-variant">
          Brief + Mockup + InterviewNote를 통합하여 최종 spec.md를 생성합니다.
        </p>
      </div>

      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-2">
        <h3 className="font-bold text-on-surface mb-2">입력 요약</h3>
        <div className="flex items-center gap-2 text-sm">
          <span className={`material-symbols-outlined ${briefOk ? 'text-green-600' : 'text-error'}`}>
            {briefOk ? 'check_circle' : 'cancel'}
          </span>
          <span>Brief: {briefOk ? `${mockupState?.briefMd?.length ?? 0}자` : '없음'}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className={`material-symbols-outlined ${mockupOk ? 'text-green-600' : 'text-error'}`}>
            {mockupOk ? 'check_circle' : 'cancel'}
          </span>
          <span>Mockup.vue: {mockupOk ? `${mockupState?.mockupVue?.length ?? 0}자` : '없음'}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className={`material-symbols-outlined ${notesOk ? 'text-green-600' : 'text-error'}`}>
            {notesOk ? 'check_circle' : 'cancel'}
          </span>
          <span>InterviewNote: {notesOk ? '생성 완료' : '없음'}</span>
        </div>
      </div>

      {isGenerating && (
        <div className="bg-surface-container-low rounded-xl p-6 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-bold text-on-surface">{statusMessage ?? '생성 중...'}</p>
        </div>
      )}

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => goToStep(3)}
          className="text-on-surface-variant hover:text-on-surface px-4 py-2 rounded-lg hover:bg-surface-container"
        >
          ← 이전
        </button>
        <button
          type="button"
          onClick={generateSpec}
          disabled={!canGenerate}
          className="gradient-button text-on-primary px-8 py-3 rounded-xl font-bold font-headline shadow-lg disabled:opacity-50 flex items-center gap-2"
        >
          <span className="material-symbols-outlined">article</span>
          {isGenerating ? 'Spec.md 생성 중...' : 'Spec.md 생성'}
        </button>
      </div>
    </div>
  )
}
