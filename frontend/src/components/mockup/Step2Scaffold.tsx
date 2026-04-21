import { useEffect, useRef, useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'
import { SCREEN_ID_INVALID_CHARS } from '../../types'

const PFY_FRONT_DEV_URL = 'http://localhost:8085'
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
          {/* Vue Mockup \ucf54\ub4dc \uc0dd\uc131 */}
          {'Vue Mockup \uCF54\uB4DC \uC0DD\uC131'}
        </h3>

        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface-variant">
            {/* \ud654\uba74 ID */}
            {'\uD654\uBA74 ID'} <span className="text-error">*</span>
          </label>
          <input
            type="text"
            value={screenId}
            onChange={(e) => setScreenId(e.target.value.replace(SCREEN_ID_INVALID_CHARS, ''))}
            placeholder={'\uC608: MNET010'}
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
                {/* \uc0dd\uc131 \uc911... */}
                {'\uC0DD\uC131 \uC911...'}
              </>
            ) : (
              <>
                <span className="material-symbols-outlined">code</span>
                {/* Vue \ucf54\ub4dc \uc0dd\uc131 */}
                {'Vue \uCF54\uB4DC \uC0DD\uC131'}
              </>
            )}
          </button>
        )}
      </div>

      {hasResult && mockupState?.vueCode && (
        <div className="space-y-4">
          <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
            <div className="flex justify-between items-center px-6 py-3 border-b border-surface-container">
              <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-tertiary">preview</span>
                {/* Mockup \ubbf8\ub9ac\ubcf4\uae30 */}
                {'Mockup \uBBF8\uB9AC\uBCF4\uAE30'}
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
                    {/* \uc0c8 \ud0ed\uc5d0\uc11c \uc5f4\uae30 */}
                    {'\uC0C8 \uD0ED\uC5D0\uC11C \uC5F4\uAE30'}
                  </a>
                )}
                <button
                  onClick={() => setShowCode(!showCode)}
                  className="text-xs text-on-surface-variant hover:text-on-surface flex items-center gap-1 px-2 py-1 rounded-md hover:bg-surface-container transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px]">
                    {showCode ? 'visibility_off' : 'code'}
                  </span>
                  {/* \ucf54\ub4dc \uc228\uae30\uae30 : \ucf54\ub4dc \ubcf4\uae30 */}
                  {showCode ? '\uCF54\uB4DC \uC228\uAE30\uAE30' : '\uCF54\uB4DC \uBCF4\uAE30'}
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
                  {previewUrl}  &middot;  {Math.round(scale * 100)}%
                </div>
              </div>
            )}
            {!previewUrl && (
              <div className="p-12 text-center text-on-surface-variant">
                {/* pfy-front Vue dev \uc11c\ubc84\uac00 \uc2e4\ud589 \uc911\uc774\uc5b4\uc57c \ubbf8\ub9ac\ubcf4\uae30\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4. */}
                <p>{'pfy-front Vue dev \uC11C\uBC84\uAC00 \uC2E4\uD589 \uC911\uC774\uC5B4\uC57C \uBBF8\uB9AC\uBCF4\uAE30\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4.'}</p>
                <code className="text-xs bg-surface-container px-2 py-1 rounded mt-2 inline-block">
                  cd pfy-front &amp;&amp; npm run dev
                </code>
              </div>
            )}
          </div>

          {showCode && (
            <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-3">
              {/* \uc0dd\uc131\ub41c Vue \ucf54\ub4dc */}
              <h4 className="text-sm font-bold text-on-surface-variant">{'\uC0DD\uC131\uB41C Vue \uCF54\uB4DC'}</h4>
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
            {/* \ub2e4\uc74c: \uc8fc\uc11d \uc0bd\uc785 */}
            {'\uB2E4\uC74C: \uC8FC\uC11D \uC0BD\uC785'}
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      )}
    </div>
  )
}
