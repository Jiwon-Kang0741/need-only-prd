import { useEffect, useRef, useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'

const PFY_FRONT_DEV_URL = 'http://localhost:8081'
const VIEWPORT_WIDTH = 1440
const VIEWPORT_HEIGHT = 900

export default function Step2Mockup() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const statusMessage = useSessionStore((s) => s.statusMessage)
  const generateMockup = useSessionStore((s) => s.mockupGenerateMockup)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const [showCode, setShowCode] = useState(false)
  const previewContainerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  useEffect(() => {
    const el = previewContainerRef.current
    if (!el) return
    const update = () => {
      const containerWidth = el.clientWidth
      setScale(containerWidth / VIEWPORT_WIDTH)
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [mockupState?.mockupVue])

  const previewUrl = mockupState?.projectId
    ? `${PFY_FRONT_DEV_URL}/${mockupState.projectId}`
    : null

  const hasMockup = !!mockupState?.mockupVue
  const isGenerating = loading && !hasMockup

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold font-headline text-on-surface mb-1">② Mockup 생성</h2>
        <p className="text-sm text-on-surface-variant">
          brief.md를 바탕으로 LLM이 Vue Mockup을 생성합니다. 화면 여러 개가 v-if로 포함되며,
          iframe에서 실제 렌더링을 볼 수 있습니다.
        </p>
      </div>

      {!hasMockup && !isGenerating && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={generateMockup}
            disabled={loading}
            className="gradient-button text-on-primary px-8 py-4 rounded-xl font-bold font-headline text-lg shadow-lg disabled:opacity-50 flex items-center gap-3"
          >
            <span className="material-symbols-outlined">auto_awesome</span>
            Mockup 생성 시작
          </button>
        </div>
      )}

      {isGenerating && (
        <div className="bg-surface-container-low rounded-xl p-6 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <div>
            <p className="text-sm font-bold text-on-surface">{statusMessage ?? '생성 중...'}</p>
            <p className="text-xs text-on-surface-variant mt-0.5">
              현재 코드 길이: {mockupState?.mockupVue?.length ?? 0} 자
            </p>
          </div>
        </div>
      )}

      {hasMockup && previewUrl && (
        <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-surface-container">
            <h3 className="font-bold text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-tertiary">preview</span>
              Mockup 미리보기
            </h3>
            <div className="flex items-center gap-2">
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                새 탭
              </a>
              <button
                onClick={() => setShowCode(!showCode)}
                className="text-xs text-on-surface-variant hover:text-on-surface flex items-center gap-1 px-2 py-1 rounded-md hover:bg-surface-container"
              >
                <span className="material-symbols-outlined text-[16px]">
                  {showCode ? 'visibility_off' : 'code'}
                </span>
                {showCode ? '코드 숨기기' : '코드 보기'}
              </button>
            </div>
          </div>
          <div
            ref={previewContainerRef}
            className="relative overflow-hidden bg-white"
            style={{ height: `${VIEWPORT_HEIGHT * scale}px` }}
          >
            <iframe
              src={previewUrl}
              className="border-0 bg-white"
              style={{
                width: `${VIEWPORT_WIDTH}px`,
                height: `${VIEWPORT_HEIGHT}px`,
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
              }}
              title="Mockup Preview"
            />
            <div className="absolute bottom-2 right-2 bg-surface-container/80 backdrop-blur-sm text-on-surface-variant text-xs px-2 py-1 rounded-md pointer-events-none">
              {previewUrl} · {Math.round(scale * 100)}%
            </div>
          </div>
        </div>
      )}

      {showCode && hasMockup && (
        <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm">
          <pre className="bg-inverse-surface text-inverse-on-surface rounded-lg p-4 text-xs overflow-auto max-h-[400px] leading-relaxed">
            {mockupState?.mockupVue}
          </pre>
        </div>
      )}

      {error && (
        <div className="bg-error-container text-on-error-container px-4 py-2 rounded-lg text-sm">{error}</div>
      )}

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => goToStep(1)}
          className="text-on-surface-variant hover:text-on-surface px-4 py-2 rounded-lg hover:bg-surface-container"
        >
          ← 이전
        </button>
        {hasMockup && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={generateMockup}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-surface-container text-on-surface hover:bg-surface-container-high disabled:opacity-50"
            >
              재생성
            </button>
            <button
              type="button"
              onClick={() => goToStep(3)}
              className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold flex items-center gap-2"
            >
              다음: 인터뷰 →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
