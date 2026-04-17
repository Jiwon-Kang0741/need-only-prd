import { useSessionStore } from '../../store/sessionStore'
import StepIndicator from './StepIndicator'
import Step1AiGenerate from './Step1AiGenerate'
import Step2Scaffold from './Step2Scaffold'
import Step3Annotate from './Step3Annotate'
import Step4Interview from './Step4Interview'
import Step5InterviewResult from './Step5InterviewResult'
import Step6SpecGenerate from './Step6SpecGenerate'

function CurrentStep({ step }: { step: number }) {
  switch (step) {
    case 1: return <Step1AiGenerate />
    case 2: return <Step2Scaffold />
    case 3: return <Step3Annotate />
    case 4: return <Step4Interview />
    case 5: return <Step5InterviewResult />
    case 6: return <Step6SpecGenerate />
    default: return <Step1AiGenerate />
  }
}

export default function MockupPipeline() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const resetMockup = useSessionStore((s) => s.resetMockup)
  const currentStep = mockupState?.currentStep ?? 1

  return (
    <div className="max-w-[768px] mx-auto space-y-6">
      {/* Hero header */}
      <div className="flex flex-col items-center text-center space-y-3 mb-2">
        <h1 className="text-[3.5rem] leading-tight font-extrabold font-headline tracking-tighter text-on-background">
          Mockup
        </h1>
        <p className="text-secondary max-w-md">
          AI가 화면을 설계하고, 인터뷰를 통해 정확한 Spec을 생성합니다.
        </p>
      </div>

      {/* Step indicator */}
      <StepIndicator />

      {/* Reset button */}
      {mockupState && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={resetMockup}
            className="text-xs text-on-surface-variant hover:text-error flex items-center gap-1 transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">restart_alt</span>
            처음부터 다시
          </button>
        </div>
      )}

      {/* Current step content */}
      <CurrentStep step={currentStep} />
    </div>
  )
}
