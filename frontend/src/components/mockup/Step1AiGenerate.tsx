import { useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'

const PAGE_TYPES = [
  { value: 'list', label: '목록형', icon: 'list' },
  { value: 'list-detail', label: '목록+상세', icon: 'view_sidebar' },
  { value: 'edit', label: '편집형', icon: 'edit_note' },
  { value: 'tab-detail', label: '탭+상세', icon: 'tab' },
]

export default function Step1AiGenerate() {
  const [title, setTitle] = useState('')
  const [pageType, setPageType] = useState('list')
  const [description, setDescription] = useState('')

  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const aiGenerate = useSessionStore((s) => s.mockupAiGenerate)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const hasResult = mockupState !== null && mockupState.currentStep >= 1 && mockupState.fields.length > 0

  async function handleGenerate() {
    if (!title.trim() || loading) return
    await aiGenerate(title.trim(), pageType, description.trim() || undefined)
  }

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-5">
        <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">draw</span>
          화면 설계 정보 입력
        </h3>

        {/* Title */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface-variant">
            화면 제목 <span className="text-error">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="예: 공지사항 관리"
            className="w-full px-4 py-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
            disabled={loading}
          />
        </div>

        {/* Page type */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface-variant">페이지 유형</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {PAGE_TYPES.map((pt) => (
              <label
                key={pt.value}
                className={`flex items-center gap-2 px-4 py-3 rounded-lg border cursor-pointer transition-all ${
                  pageType === pt.value
                    ? 'border-primary bg-primary-fixed/30 text-primary font-bold'
                    : 'border-outline-variant bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-low'
                }`}
              >
                <input
                  type="radio"
                  name="pageType"
                  value={pt.value}
                  checked={pageType === pt.value}
                  onChange={(e) => setPageType(e.target.value)}
                  className="sr-only"
                />
                <span className="material-symbols-outlined text-[20px]">{pt.icon}</span>
                <span className="text-sm">{pt.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Description */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface-variant">설명 (선택)</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="화면에 대한 추가 설명이나 요구사항을 입력하세요..."
            className="w-full min-h-[100px] px-4 py-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:border-primary focus:ring-1 focus:ring-primary transition-colors resize-y"
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
          onClick={handleGenerate}
          disabled={!title.trim() || loading}
          className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          {loading ? (
            <>
              <svg className="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              AI 설계 중...
            </>
          ) : (
            <>
              <span className="material-symbols-outlined">auto_awesome</span>
              AI 설계 시작
            </>
          )}
        </button>
      </div>

      {/* Result preview */}
      {hasResult && mockupState && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-4">
          <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-tertiary">check_circle</span>
            설계 결과
          </h3>
          <pre className="bg-inverse-surface text-inverse-on-surface rounded-lg p-4 text-xs overflow-x-auto max-h-[300px] overflow-y-auto">
            {JSON.stringify({ screenName: mockupState.screenName, pageType: mockupState.pageType, fields: mockupState.fields }, null, 2)}
          </pre>

          <button
            type="button"
            onClick={() => goToStep(2)}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2"
          >
            다음: Mockup 생성
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      )}
    </div>
  )
}
