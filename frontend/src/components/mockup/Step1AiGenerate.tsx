import { useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'

const PAGE_TYPES = [
  {
    value: 'list',
    label: '목록형',
    desc: 'Multiple items display',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <rect x="2" y="5" width="24" height="3" rx="1.5" fill="currentColor" opacity=".9"/>
        <rect x="2" y="12" width="24" height="3" rx="1.5" fill="currentColor" opacity=".6"/>
        <rect x="2" y="19" width="24" height="3" rx="1.5" fill="currentColor" opacity=".3"/>
      </svg>
    ),
  },
  {
    value: 'list-detail',
    label: '목록+상세',
    desc: 'Split view exploration',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <rect x="2" y="4" width="10" height="20" rx="2" fill="currentColor" opacity=".7"/>
        <rect x="15" y="4" width="11" height="9" rx="2" fill="currentColor" opacity=".9"/>
        <rect x="15" y="15" width="11" height="9" rx="2" fill="currentColor" opacity=".4"/>
      </svg>
    ),
  },
  {
    value: 'edit',
    label: '편집형',
    desc: 'Form-heavy interaction',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <rect x="2" y="4" width="24" height="3" rx="1.5" fill="currentColor" opacity=".4"/>
        <rect x="2" y="10" width="24" height="3" rx="1.5" fill="currentColor" opacity=".9"/>
        <rect x="2" y="16" width="16" height="3" rx="1.5" fill="currentColor" opacity=".6"/>
        <path d="M21 19l4-4-2-2-4 4v2h2z" fill="currentColor" opacity=".9"/>
      </svg>
    ),
  },
  {
    value: 'tab-detail',
    label: '탭+상세',
    desc: 'Complex categorized data',
    icon: (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <rect x="2" y="4" width="7" height="5" rx="2" fill="currentColor" opacity=".9"/>
        <rect x="11" y="4" width="7" height="5" rx="2" fill="currentColor" opacity=".4"/>
        <rect x="20" y="4" width="6" height="5" rx="2" fill="currentColor" opacity=".4"/>
        <rect x="2" y="11" width="24" height="13" rx="2" fill="currentColor" opacity=".6"/>
      </svg>
    ),
  },
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
    <div className="flex flex-col h-full">
      {/* ── Header ── */}
      <div className="px-10 pt-8 pb-6" style={{ borderBottom: '1px solid #1e1e1e' }}>
        <h1
          className="text-3xl font-extrabold text-white mb-1"
          style={{ fontFamily: 'Manrope, sans-serif' }}
        >
          화면 설계 정보 입력
        </h1>
        <p className="text-sm" style={{ color: '#666666' }}>
          Fill in the core details to generate your project design system.
        </p>
      </div>

      {/* ── Form ── */}
      <div className="flex-1 overflow-y-auto px-10 py-8 space-y-8">

        {/* 화면 제목 */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">
            화면 제목 <span style={{ color: '#f4821f' }}>*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
            placeholder="예: 고객 대시보드 메인"
            disabled={loading}
            className="dark-input"
          />
        </div>

        {/* 페이지 유형 */}
        <div>
          <label className="block text-sm font-semibold text-white mb-3">페이지 유형</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {PAGE_TYPES.map((pt) => {
              const isSelected = pageType === pt.value
              return (
                <button
                  key={pt.value}
                  type="button"
                  onClick={() => setPageType(pt.value)}
                  disabled={loading}
                  className="page-type-card"
                  style={
                    isSelected
                      ? { borderColor: '#f4821f', background: 'rgba(244,130,31,0.06)' }
                      : {}
                  }
                >
                  {/* Checkmark badge (selected only) */}
                  {isSelected && (
                    <span className="check-badge">
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </span>
                  )}
                  {/* Icon */}
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{
                      background: isSelected ? 'rgba(244,130,31,0.15)' : '#1e1e1e',
                      color: isSelected ? '#f4821f' : '#666666',
                    }}
                  >
                    {pt.icon}
                  </div>
                  {/* Labels */}
                  <div>
                    <div
                      className="text-sm font-bold leading-tight"
                      style={{ color: isSelected ? '#ffffff' : '#cccccc' }}
                    >
                      {pt.label}
                    </div>
                    <div className="text-[11px] mt-0.5" style={{ color: '#555555' }}>
                      {pt.desc}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* 설명 */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-semibold text-white">설명 (선택)</label>
            <span className="text-xs" style={{ color: '#555555' }}>Markdown supported</span>
          </div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="화면의 목적이나 주요 기능 요구사항을 입력해 주세요..."
            rows={6}
            disabled={loading}
            className="dark-input resize-y"
          />
        </div>

        {/* Error */}
        {error && (
          <div
            className="text-sm px-4 py-3 rounded-lg"
            style={{ background: 'rgba(255,107,107,0.1)', color: '#ff6b6b', border: '1px solid rgba(255,107,107,0.2)' }}
          >
            {error}
          </div>
        )}

        {/* Result preview (after generation) */}
        {hasResult && mockupState && (
          <div
            className="rounded-xl p-5 space-y-3"
            style={{ background: '#161616', border: '1px solid #2a2a2a' }}
          >
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]" style={{ color: '#f4821f' }}>check_circle</span>
              <span className="text-sm font-semibold text-white">설계 결과</span>
            </div>
            <pre
              className="text-xs overflow-x-auto rounded-lg p-4 no-scrollbar"
              style={{ background: '#0f0f0f', color: '#aaaaaa' }}
            >
              {JSON.stringify(
                { screenName: mockupState.screenName, pageType: mockupState.pageType, fields: mockupState.fields },
                null,
                2,
              )}
            </pre>
            <button
              type="button"
              onClick={() => goToStep(2)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold transition-colors"
              style={{ background: '#f4821f', color: '#fff' }}
            >
              다음: Mockup 생성
              <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
            </button>
          </div>
        )}
      </div>

      {/* ── Bottom Action Bar ── */}
      <div
        className="px-10 py-4 flex items-center justify-between"
        style={{ borderTop: '1px solid #1e1e1e', background: '#0f0f0f' }}
      >
        <div className="flex items-center gap-2 text-xs" style={{ color: '#555555' }}>
          <span className="material-symbols-outlined text-[16px]" style={{ color: '#f4821f' }}>auto_awesome</span>
          AI will generate 12+ components based on your input
        </div>

        <button
          type="button"
          onClick={handleGenerate}
          disabled={!title.trim() || loading}
          className="flex items-center gap-2 px-7 py-3 rounded-xl text-sm font-bold transition-all"
          style={{
            background: !title.trim() || loading ? '#2a2a2a' : '#f4821f',
            color: !title.trim() || loading ? '#555555' : '#ffffff',
            cursor: !title.trim() || loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? (
            <>
              <svg className="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              AI 설계 중...
            </>
          ) : (
            <>
              <span className="text-base">⚡</span>
              AI 설계 시작
            </>
          )}
        </button>
      </div>
    </div>
  )
}
