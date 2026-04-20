interface Props {
  currentStep: number
  onStepClick?: (step: number) => void
}

const STEPS = [
  { num: 1, label: 'Brief', desc: '프로젝트 정보' },
  { num: 2, label: 'Mockup', desc: 'Vue 생성 & 미리보기' },
  { num: 3, label: '인터뷰', desc: '원천 → InterviewNote' },
  { num: 4, label: 'Spec', desc: '최종 spec.md' },
]

export default function StepIndicator({ currentStep, onStepClick }: Props) {
  return (
    <div className="flex items-center gap-2 justify-center flex-wrap mb-6">
      {STEPS.map((s, idx) => {
        const isActive = s.num === currentStep
        const isDone = s.num < currentStep
        const clickable = isDone && !!onStepClick

        return (
          <div key={s.num} className="flex items-center">
            <button
              type="button"
              onClick={() => clickable && onStepClick?.(s.num)}
              disabled={!clickable && !isActive}
              className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${
                isActive
                  ? 'bg-primary text-on-primary shadow-md'
                  : isDone
                  ? 'bg-primary-fixed text-on-primary-fixed cursor-pointer hover:brightness-95'
                  : 'bg-surface-container text-on-surface-variant'
              }`}
            >
              <span className={`inline-flex w-6 h-6 items-center justify-center rounded-full text-xs font-bold ${
                isActive ? 'bg-on-primary/20' : isDone ? 'bg-on-primary-fixed/20' : 'bg-outline-variant/50'
              }`}>
                {isDone ? '✓' : s.num}
              </span>
              <span className="text-sm font-bold font-headline">{s.label}</span>
            </button>
            {idx < STEPS.length - 1 && (
              <div className={`w-6 h-[2px] ${isDone ? 'bg-primary-fixed' : 'bg-surface-container'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
