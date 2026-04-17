import { useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'

export default function Step2Scaffold() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const scaffold = useSessionStore((s) => s.mockupScaffold)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const [screenId, setScreenId] = useState(mockupState?.screenId ?? '')

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
            onChange={(e) => setScreenId(e.target.value)}
            placeholder="예: SCR001"
            className="w-full px-4 py-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
            disabled={loading}
          />
        </div>

        {error && (
          <div className="text-sm text-error bg-error-container/30 px-4 py-2 rounded-lg">
            {error}
          </div>
        )}

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
      </div>

      {hasResult && mockupState?.vueCode && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-4">
          <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-tertiary">check_circle</span>
            생성된 Vue 코드
          </h3>
          <pre className="bg-inverse-surface text-inverse-on-surface rounded-lg p-4 text-xs overflow-x-auto max-h-[400px] overflow-y-auto leading-relaxed">
            {mockupState.vueCode}
          </pre>

          <button
            type="button"
            onClick={() => goToStep(3)}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2"
          >
            다음: 주석 삽입
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      )}
    </div>
  )
}
