import { useEffect, useRef, useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'
import { SCREEN_ID_INVALID_CHARS } from '../../types'

const PFY_FRONT_DEV_URL = 'http://localhost:8081'
const VIEWPORT_WIDTH = 1440
const VIEWPORT_HEIGHT = 900

export default function Step2Scaffold() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const scaffold = useSessionStore((s) => s.mockupScaffold)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const [screenId, setScreenId] = useState(mockupState?.screenId ?? '')
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
  }, [mockupState?.vueCode])

  const hasResult = mockupState?.vueCode !== null

  async function handleScaffold() {
    if (!screenId.trim() || loading || !mockupState) return
    await scaffold(
      screenId.trim(),
      mockupState.screenName,
      mockupState.pageType,
      mockupState.fields as Record<string, unknown>[],
    )
  }

  const previewUrl = screenId ? `${PFY_FRONT_DEV_URL}/${screenId.trim().toUpperCase()}` : null

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-5">
        <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">devices</span>
          Vue Mockup 코드 생성
        </h3>

        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface-variant">
            화면 ID <span className="text-error">*</span>
          </label>
          <input
            type="text"
            value={screenId}
            onChange={(e) => setScreenId(e.target.value.replace(SCREEN_ID_INVALID_CHARS, ''))}
            placeholder="예: MNET010"
            className="w-full px-4 py-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:border-primary focus:ring-1 focus:ring-primary transition-colors font-mono"
            disabled={loading}
          />
        </div>

        {error && (
          <div className="text-sm text-error bg-error-container/30 px-4 py-2 rounded-lg">
            {error}
          </div>
        )}

        {!hasResult && (
          <button
            type="button"
            onClick={handleScaffold}
            disabled={!screenId.trim() || loading}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {loading ? (
              <>
                <svg className="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                생성 중...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined">code</span>
                Vue 코드 생성
              </>
            )}
          </button>
        )}
      </div>

      {hasResult && mockupState?.vueCode && (
        <div className="space-y-4">
          {/* Mockup 미리보기 (iframe) */}
          <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
            <div className="flex justify-between items-center px-6 py-3 border-b border-surface-container">
              <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-tertiary">preview</span>
                Mockup 미리보기
              </h3>
              <div className="flex items-center gap-2">
                {previewUrl && (
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                    새 탭에서 열기
                  </a>
                )}
                <button
                  onClick={() => setShowCode(!showCode)}
                  className="text-xs text-on-surface-variant hover:text-on-surface flex items-center gap-1 px-2 py-1 rounded-md hover:bg-surface-container transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px]">
                    {showCode ? 'visibility_off' : 'code'}
                  </span>
                  {showCode ? '코드 숨기기' : '코드 보기'}
                </button>
              </div>
            </div>
            {previewUrl && (
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
                  {previewUrl}  ·  {Math.round(scale * 100)}%
                </div>
              </div>
            )}
            {!previewUrl && (
              <div className="p-12 text-center text-on-surface-variant">
                <p>pfy-front Vue dev 서버가 실행 중이어야 미리보기가 표시됩니다.</p>
                <code className="text-xs bg-surface-container px-2 py-1 rounded mt-2 inline-block">
                  cd pfy-front && npm run dev
                </code>
              </div>
            )}
          </div>

          {/* 코드 보기 (토글) */}
          {showCode && (
            <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-3">
              <h4 className="text-sm font-bold text-on-surface-variant">생성된 Vue 코드</h4>
              <pre className="bg-inverse-surface text-inverse-on-surface rounded-lg p-4 text-xs overflow-x-auto max-h-[400px] overflow-y-auto leading-relaxed">
                {mockupState.vueCode}
              </pre>
            </div>
          )}

          <button
            type="button"
            onClick={() => goToStep(3)}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2 w-full justify-center"
          >
            다음: 주석 삽입
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      )}
    </div>
  )
}
