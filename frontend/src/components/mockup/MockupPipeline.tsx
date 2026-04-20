import { useSessionStore } from '../../store/sessionStore'
import Step1Brief from './Step1Brief'
import Step2Mockup from './Step2Mockup'
import Step3Interview from './Step3Interview'
import Step4SpecGenerate from './Step4SpecGenerate'
import StepIndicator from './StepIndicator'

export default function MockupPipeline() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const resetMockup = useSessionStore((s) => s.resetMockup)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const currentStep = mockupState?.currentStep ?? 1

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold font-headline text-on-surface">Mockup 파이프라인</h1>
        {mockupState && (
          <button
            type="button"
            onClick={() => {
              if (confirm('진행 중인 Mockup 작업이 모두 초기화됩니다. 계속하시겠습니까?')) {
                resetMockup()
              }
            }}
            className="text-sm text-on-surface-variant hover:text-error px-3 py-1 rounded-lg hover:bg-error-container/30"
          >
            처음부터 다시
          </button>
        )}
      </div>

      <StepIndicator currentStep={currentStep} onStepClick={goToStep} />

      {currentStep === 1 && <Step1Brief />}
      {currentStep === 2 && <Step2Mockup />}
      {currentStep === 3 && <Step3Interview />}
      {currentStep === 4 && <Step4SpecGenerate />}
    </div>
  )
}
