import { useSessionStore } from '../../store/sessionStore'

const STEPS = [
  { num: 1, label: '화면설계', icon: 'draw' },
  { num: 2, label: 'Mockup', icon: 'devices' },
  { num: 3, label: '주석', icon: 'comment' },
  { num: 4, label: '인터뷰', icon: 'forum' },
  { num: 5, label: '결과', icon: 'summarize' },
  { num: 6, label: 'Spec', icon: 'description' },
]

export default function StepIndicator() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const currentStep = mockupState?.currentStep ?? 1

  return (
    <div className="flex items-center justify-center gap-1 py-4">
      {STEPS.map((step, idx) => {
        const isActive = step.num === currentStep
        const isCompleted = step.num < currentStep
        const canClick = isCompleted

        return (
          <div key={step.num} className="flex items-center">
            <button
              type="button"
              disabled={!canClick}
              onClick={() => canClick && goToStep(step.num)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-full text-xs font-bold transition-all ${
                isActive
                  ? 'bg-primary text-on-primary shadow-md'
                  : isCompleted
                  ? 'bg-primary-fixed text-on-primary-fixed cursor-pointer hover:bg-primary-fixed-dim'
                  : 'bg-surface-container text-on-surface-variant cursor-default'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">{step.icon}</span>
              <span className="hidden sm:inline">{step.label}</span>
              <span className="sm:hidden">{step.num}</span>
            </button>
            {idx < STEPS.length - 1 && (
              <div
                className={`w-4 h-0.5 mx-0.5 rounded-full ${
                  step.num < currentStep ? 'bg-primary' : 'bg-surface-container-high'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
