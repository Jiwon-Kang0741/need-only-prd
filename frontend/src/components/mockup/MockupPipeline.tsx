import { useSessionStore } from '../../store/sessionStore'
import Step1AiGenerate from './Step1AiGenerate'
import Step2Scaffold from './Step2Scaffold'
import Step3Annotate from './Step3Annotate'
import Step4Interview from './Step4Interview'
import Step5InterviewResult from './Step5InterviewResult'
import Step6SpecGenerate from './Step6SpecGenerate'
import Step7CodeGen from './Step7CodeGen'

const STEPS = [
  { num: 1, label: '화면설계', sublabel: 'AI Screen Design', icon: 'draw' },
  { num: 2, label: 'Mockup', sublabel: 'Preview Generation', icon: 'devices' },
  { num: 3, label: '주석 분석', sublabel: 'Annotation', icon: 'comment' },
  { num: 4, label: '인터뷰', sublabel: 'Requirements Interview', icon: 'forum' },
  { num: 5, label: '결과 정리', sublabel: 'Interview Result', icon: 'summarize' },
  { num: 6, label: 'Spec 생성', sublabel: 'Spec Generation', icon: 'description' },
  { num: 7, label: 'Code 생성', sublabel: 'Code Generation', icon: 'code' },
]

function CurrentStep({ step }: { step: number }) {
  switch (step) {
    case 1: return <Step1AiGenerate />
    case 2: return <Step2Scaffold />
    case 3: return <Step3Annotate />
    case 4: return <Step4Interview />
    case 5: return <Step5InterviewResult />
    case 6: return <Step6SpecGenerate />
    case 7: return <Step7CodeGen />
    default: return <Step1AiGenerate />
  }
}

export default function MockupPipeline() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const resetMockup = useSessionStore((s) => s.resetMockup)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)
  const currentStep = mockupState?.currentStep ?? 1
  const progressPct = Math.min(100, Math.round(((currentStep - 1) / (STEPS.length - 1)) * 100))

  return (
    <div className="flex h-[calc(100vh-57px)]" style={{ background: '#0f0f0f' }}>

      {/* ── Left Sidebar ── */}
      <aside
        className="flex flex-col flex-shrink-0 w-56"
        style={{
          background: '#111111',
          borderRight: '1px solid #1e1e1e',
        }}
      >
        {/* Project info */}
        <div className="p-4" style={{ borderBottom: '1px solid #1e1e1e' }}>
          <div className="flex items-center gap-2 mb-1">
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
              style={{ background: '#f4821f', color: '#fff' }}
            >
              N
            </div>
            <span className="text-sm font-semibold text-white">New Initiative</span>
          </div>
          <div className="text-[10px] font-bold tracking-widest" style={{ color: '#f4821f' }}>
            WIZARD PROGRESS: {progressPct}%
          </div>
          {/* Progress bar */}
          <div className="mt-2 h-1 rounded-full overflow-hidden" style={{ background: '#2a2a2a' }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%`, background: '#f4821f' }}
            />
          </div>
        </div>

        {/* Step nav */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {STEPS.map((step) => {
            const isActive = step.num === currentStep
            const isCompleted = step.num < currentStep
            const canClick = isCompleted

            return (
              <button
                key={step.num}
                type="button"
                disabled={!canClick}
                onClick={() => canClick && goToStep(step.num)}
                className="sidebar-nav-item w-full text-left"
                style={{
                  ...(isActive ? { background: 'rgba(244,130,31,0.12)', color: '#f4821f' } : {}),
                  ...(isCompleted ? { color: '#aaaaaa', cursor: 'pointer' } : {}),
                }}
              >
                <span
                  className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0"
                  style={{
                    background: isActive
                      ? '#f4821f'
                      : isCompleted
                      ? '#2a2a2a'
                      : '#1e1e1e',
                  }}
                >
                  {isCompleted ? (
                    <span className="material-symbols-outlined text-[14px]" style={{ color: '#f4821f' }}>
                      check
                    </span>
                  ) : (
                    <span
                      className="material-symbols-outlined text-[14px]"
                      style={{ color: isActive ? '#fff' : '#555' }}
                    >
                      {step.icon}
                    </span>
                  )}
                </span>
                <div>
                  <div className="text-[13px] font-semibold leading-tight">{step.label}</div>
                  <div className="text-[10px] leading-tight mt-0.5" style={{ color: isActive ? '#f4821f99' : '#444' }}>
                    {step.sublabel}
                  </div>
                </div>
              </button>
            )
          })}
        </nav>

        {/* Bottom area */}
        <div className="p-3 space-y-2" style={{ borderTop: '1px solid #1e1e1e' }}>
          <button
            type="button"
            className="sidebar-nav-item w-full text-left"
            style={{ color: '#666' }}
          >
            <span className="material-symbols-outlined text-[18px]">help_outline</span>
            <span className="text-[13px]">Help Center</span>
          </button>

          {mockupState && (
            <button
              type="button"
              onClick={resetMockup}
              className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-colors"
              style={{
                background: '#1e1e1e',
                color: '#888',
                border: '1px solid #2a2a2a',
              }}
            >
              <span className="material-symbols-outlined text-[15px]">restart_alt</span>
              Save Draft
            </button>
          )}
        </div>
      </aside>

      {/* ── Main Content ── */}
      <div className="flex-1 overflow-y-auto p-6">
        <CurrentStep step={currentStep} />
      </div>
    </div>
  )
}
