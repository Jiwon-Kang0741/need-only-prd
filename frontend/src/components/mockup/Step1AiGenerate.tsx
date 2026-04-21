import { useState, useEffect } from 'react'
import { useSessionStore } from '../../store/sessionStore'
import { SCREEN_ID_INVALID_CHARS } from '../../types'

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

const FIELD_TYPES = [
  { value: 'text', label: '텍스트' },
  { value: 'number', label: '숫자' },
  { value: 'date', label: '날짜' },
  { value: 'daterange', label: '날짜범위' },
  { value: 'select', label: '선택' },
  { value: 'checkbox', label: '체크박스' },
]

const ACTION_OPTIONS = [
  { value: 'create', label: '등록 (create)' },
  { value: 'excel', label: '엑셀 다운로드 (excel)' },
  { value: 'detail', label: '상세 (detail)' },
  { value: 'delete', label: '삭제 (delete)' },
]

interface SearchField {
  key: string
  label: string
  type: string
  optionsText: string
}

interface TableColumn {
  key: string
  label: string
}

function sanitizeKey(raw: string): string {
  return raw.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_$]/g, '')
}

export default function Step1AiGenerate() {
  const [title, setTitle] = useState('')
  const [pageType, setPageType] = useState('list')
  const [description, setDescription] = useState('')
  const [screenId, setScreenId] = useState('')

  // Phase 2 editable fields
  const [searchFields, setSearchFields] = useState<SearchField[]>([])
  const [tableColumns, setTableColumns] = useState<TableColumn[]>([])
  const [actionFlags, setActionFlags] = useState<Record<string, boolean>>({
    create: false, excel: false, detail: false, delete: false,
  })
  const [mockDataCount, setMockDataCount] = useState(10)

  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const aiGenerate = useSessionStore((s) => s.mockupAiGenerate)
  const scaffold = useSessionStore((s) => s.mockupScaffold)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const hasAiResult = mockupState !== null && mockupState.fields.length > 0

  // Populate local editable fields from AI result
  useEffect(() => {
    if (!mockupState?.fields?.length) return
    const fields = mockupState.fields as Record<string, unknown>[]

    setSearchFields(
      fields
        .filter((f) => f.searchable)
        .map((f) => ({
          key: (f.key as string) || '',
          label: (f.label as string) || '',
          type: (f.type as string) || 'text',
          optionsText: Array.isArray(f.options)
            ? (f.options as { value: string; label: string }[]).map((o) => `${o.value}:${o.label}`).join(', ')
            : '',
        })),
    )
    setTableColumns(
      fields
        .filter((f) => f.listable)
        .map((f) => ({ key: (f.key as string) || '', label: (f.label as string) || '' })),
    )
    setScreenId(mockupState.screenId || '')
  }, [mockupState?.screenId, mockupState?.fields])

  async function handleAiGenerate() {
    if (!title.trim() || loading) return
    await aiGenerate(title.trim(), pageType, description.trim() || undefined)
  }

  async function handleScaffold() {
    if (!screenId.trim() || loading || !mockupState) return

    // Merge search fields + table columns into normalized field defs
    const fieldMap = new Map<string, Record<string, unknown>>()
    searchFields.forEach((f) => {
      const entry: Record<string, unknown> = { key: f.key, label: f.label, type: f.type, searchable: true }
      if (f.type === 'select' && f.optionsText.trim()) {
        entry.options = f.optionsText.split(',').map((s) => {
          const [v, l] = s.trim().split(':')
          return { value: v?.trim() ?? s.trim(), label: l?.trim() ?? v?.trim() ?? s.trim() }
        })
      }
      fieldMap.set(f.key, entry)
    })
    tableColumns.forEach((c) => {
      const existing = fieldMap.get(c.key)
      if (existing) {
        existing.listable = true
      } else {
        fieldMap.set(c.key, { key: c.key, label: c.label, listable: true })
      }
    })

    const allFields = Array.from(fieldMap.values())
    await scaffold(screenId.trim(), title.trim() || mockupState.screenName, pageType, allFields)
    goToStep(2)
  }

  // ─── Search Field helpers ───
  function addSearchField() {
    setSearchFields((prev) => [...prev, { key: '', label: '', type: 'text', optionsText: '' }])
  }
  function removeSearchField(i: number) {
    setSearchFields((prev) => prev.filter((_, idx) => idx !== i))
  }
  function updateSearchField(i: number, patch: Partial<SearchField>) {
    setSearchFields((prev) => prev.map((f, idx) => (idx === i ? { ...f, ...patch } : f)))
  }

  // ─── Table Column helpers ───
  function addTableColumn() {
    setTableColumns((prev) => [...prev, { key: '', label: '' }])
  }
  function removeTableColumn(i: number) {
    setTableColumns((prev) => prev.filter((_, idx) => idx !== i))
  }
  function updateTableColumn(i: number, patch: Partial<TableColumn>) {
    setTableColumns((prev) => prev.map((c, idx) => (idx === i ? { ...c, ...patch } : c)))
  }

  const inputStyle: React.CSSProperties = {
    background: '#242424',
    border: '1px solid #333',
    color: '#fff',
    borderRadius: 6,
    padding: '6px 10px',
    fontSize: 13,
    outline: 'none',
    width: '100%',
    boxSizing: 'border-box',
  }

  const selectStyle: React.CSSProperties = {
    ...inputStyle,
    padding: '5px 8px',
    cursor: 'pointer',
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
          화면 제목/설명 기반으로 필드를 자동 추천합니다
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
            onKeyDown={(e) => e.key === 'Enter' && handleAiGenerate()}
            placeholder="예: 교육이수현황 목록"
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
                  {isSelected && (
                    <span className="check-badge">
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6l3 3 5-5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </span>
                  )}
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{
                      background: isSelected ? 'rgba(244,130,31,0.15)' : '#1e1e1e',
                      color: isSelected ? '#f4821f' : '#666666',
                    }}
                  >
                    {pt.icon}
                  </div>
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
            <span className="text-xs" style={{ color: '#555555' }}>AI 추천 품질 향상</span>
          </div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="화면의 목적이나 주요 기능 요구사항을 입력해 주세요..."
            rows={3}
            disabled={loading}
            className="dark-input resize-y"
          />
        </div>

        {/* AI 자동생성 버튼 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '12px 16px',
            background: '#111',
            border: '1px solid #222',
            borderRadius: 10,
          }}
        >
          <button
            type="button"
            onClick={handleAiGenerate}
            disabled={!title.trim() || loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 20px',
              borderRadius: 8,
              fontWeight: 700,
              fontSize: 14,
              background: !title.trim() || loading ? '#2a2a2a' : '#f4821f',
              color: !title.trim() || loading ? '#555' : '#fff',
              border: 'none',
              cursor: !title.trim() || loading ? 'not-allowed' : 'pointer',
              transition: 'background 0.15s',
            }}
          >
            {loading && !hasAiResult ? (
              <>
                <svg className="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                생성 중...
              </>
            ) : (
              <>
                <span style={{ fontSize: 16 }}>⚡</span>
                AI 자동생성
              </>
            )}
          </button>
          <span style={{ fontSize: 12, color: '#3b82f6' }}>
            화면 제목/설명 기반으로 필드를 자동 추천합니다
          </span>
          {error && (
            <span style={{ fontSize: 12, color: '#ef4444', marginLeft: 'auto' }}>{error}</span>
          )}
        </div>

        {/* ── Phase 2: 생성 결과 (검색 필드 + 테이블 컬럼) ── */}
        {hasAiResult && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

            {/* 검색 필드 */}
            {pageType === 'list' && (
              <section
                style={{
                  background: '#161616',
                  border: '1px solid #2a2a2a',
                  borderRadius: 10,
                  padding: '16px 20px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 600, color: '#c0c0c0', margin: 0 }}>검색 필드</h3>
                  <button
                    type="button"
                    onClick={addSearchField}
                    style={{
                      fontSize: 12, fontWeight: 600, color: '#f4821f',
                      background: 'transparent', border: '1px solid #f4821f',
                      borderRadius: 6, padding: '3px 10px', cursor: 'pointer',
                    }}
                  >
                    + 추가
                  </button>
                </div>

                {searchFields.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {/* Header */}
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr 120px 1fr 28px',
                      gap: 6,
                      fontSize: 11,
                      color: '#606060',
                      paddingBottom: 4,
                      borderBottom: '1px solid #222',
                    }}>
                      <span>Key (영문만)</span>
                      <span>레이블</span>
                      <span>타입</span>
                      <span>옵션</span>
                      <span />
                    </div>

                    {searchFields.map((field, i) => (
                      <div key={i}>
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr 120px 1fr 28px',
                          gap: 6,
                          alignItems: 'center',
                        }}>
                          <input
                            style={inputStyle}
                            value={field.key}
                            placeholder="key (영문)"
                            onChange={(e) => updateSearchField(i, { key: sanitizeKey(e.target.value) })}
                          />
                          <input
                            style={inputStyle}
                            value={field.label}
                            placeholder="레이블"
                            onChange={(e) => updateSearchField(i, { label: e.target.value })}
                          />
                          <select
                            style={selectStyle}
                            value={field.type}
                            onChange={(e) => updateSearchField(i, { type: e.target.value })}
                          >
                            {FIELD_TYPES.map((t) => (
                              <option key={t.value} value={t.value}>{t.label}</option>
                            ))}
                          </select>
                          <span style={{ fontSize: 11, color: '#606060', fontStyle: 'italic' }}>
                            {field.type === 'daterange' ? 'from ~ to 자동 생성' :
                             field.type === 'select' ? '아래에서 설정' :
                             field.type === 'checkbox' ? 'true/false 필터' : ''}
                          </span>
                          <button
                            type="button"
                            onClick={() => removeSearchField(i)}
                            style={{
                              width: 28, height: 28, background: 'transparent',
                              border: 'none', color: '#606060', cursor: 'pointer',
                              fontSize: 12, borderRadius: 4, display: 'flex',
                              alignItems: 'center', justifyContent: 'center',
                            }}
                          >
                            ✕
                          </button>
                        </div>
                        {field.type === 'select' && (
                          <div style={{ marginTop: 4, marginBottom: 4 }}>
                            <input
                              style={{ ...inputStyle, fontSize: 12 }}
                              value={field.optionsText}
                              placeholder="v1:라벨1, v2:라벨2 (예: ONLINE:온라인, OFFLINE:오프라인)"
                              onChange={(e) => updateSearchField(i, { optionsText: e.target.value })}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontSize: 12, color: '#444', textAlign: 'center', padding: '12px 0', margin: 0 }}>
                    검색 필드가 없습니다.
                  </p>
                )}
              </section>
            )}

            {/* 테이블 컬럼 */}
            {pageType === 'list' && (
              <section
                style={{
                  background: '#161616',
                  border: '1px solid #2a2a2a',
                  borderRadius: 10,
                  padding: '16px 20px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <h3 style={{ fontSize: 13, fontWeight: 600, color: '#c0c0c0', margin: 0 }}>테이블 컬럼</h3>
                  <button
                    type="button"
                    onClick={addTableColumn}
                    style={{
                      fontSize: 12, fontWeight: 600, color: '#f4821f',
                      background: 'transparent', border: '1px solid #f4821f',
                      borderRadius: 6, padding: '3px 10px', cursor: 'pointer',
                    }}
                  >
                    + 추가
                  </button>
                </div>

                {tableColumns.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr 28px',
                      gap: 6,
                      fontSize: 11,
                      color: '#606060',
                      paddingBottom: 4,
                      borderBottom: '1px solid #222',
                    }}>
                      <span>Key (영문만)</span>
                      <span>헤더명</span>
                      <span />
                    </div>
                    {tableColumns.map((col, i) => (
                      <div key={i} style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr 28px',
                        gap: 6,
                        alignItems: 'center',
                      }}>
                        <input
                          style={inputStyle}
                          value={col.key}
                          placeholder="key (영문)"
                          onChange={(e) => updateTableColumn(i, { key: sanitizeKey(e.target.value) })}
                        />
                        <input
                          style={inputStyle}
                          value={col.label}
                          placeholder="헤더명"
                          onChange={(e) => updateTableColumn(i, { label: e.target.value })}
                        />
                        <button
                          type="button"
                          onClick={() => removeTableColumn(i)}
                          style={{
                            width: 28, height: 28, background: 'transparent',
                            border: 'none', color: '#606060', cursor: 'pointer',
                            fontSize: 12, borderRadius: 4, display: 'flex',
                            alignItems: 'center', justifyContent: 'center',
                          }}
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontSize: 12, color: '#444', textAlign: 'center', padding: '12px 0', margin: 0 }}>
                    컬럼이 없습니다.
                  </p>
                )}
              </section>
            )}

            {/* 버튼 액션 */}
            <section
              style={{
                background: '#161616',
                border: '1px solid #2a2a2a',
                borderRadius: 10,
                padding: '16px 20px',
              }}
            >
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#c0c0c0', margin: '0 0 12px 0' }}>버튼 액션</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20 }}>
                {ACTION_OPTIONS.map((action) => (
                  <label
                    key={action.value}
                    style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13, color: '#ccc' }}
                  >
                    <input
                      type="checkbox"
                      checked={!!actionFlags[action.value]}
                      onChange={(e) => setActionFlags((prev) => ({ ...prev, [action.value]: e.target.checked }))}
                      style={{ accentColor: '#f4821f', width: 15, height: 15 }}
                    />
                    {action.label}
                  </label>
                ))}
              </div>
            </section>

            {/* 목업 데이터 수 */}
            <section
              style={{
                background: '#161616',
                border: '1px solid #2a2a2a',
                borderRadius: 10,
                padding: '16px 20px',
              }}
            >
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#c0c0c0', margin: '0 0 12px 0' }}>목업 데이터 수</h3>
              <input
                type="number"
                min={1}
                max={100}
                value={mockDataCount}
                onChange={(e) => setMockDataCount(Math.max(1, Math.min(100, Number(e.target.value))))}
                style={{ ...inputStyle, width: 120 }}
              />
            </section>

            {/* 화면 ID */}
            <section
              style={{
                background: '#161616',
                border: '1px solid #2a2a2a',
                borderRadius: 10,
                padding: '16px 20px',
              }}
            >
              <h3 style={{ fontSize: 13, fontWeight: 600, color: '#c0c0c0', margin: '0 0 4px 0' }}>
                화면 ID <span style={{ color: '#f4821f' }}>*</span>
              </h3>
              <p style={{ fontSize: 11, color: '#555', margin: '0 0 10px 0' }}>
                생성 파일명 및 라우트에 사용됩니다 (영문/숫자/언더스코어)
              </p>
              <input
                type="text"
                value={screenId}
                onChange={(e) => setScreenId(e.target.value.replace(SCREEN_ID_INVALID_CHARS, ''))}
                placeholder="예: EDU_A001"
                style={{ ...inputStyle, fontFamily: 'Consolas, Monaco, monospace' }}
              />
            </section>

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
          {hasAiResult
            ? '클릭 시 목업 파일 생성 → 주석(LLM) → 인터뷰(LLM) 순으로 진행됩니다.'
            : 'AI will generate fields based on your input'}
        </div>

        {/* Phase 2: AI 설계 버튼 (scaffold 실행) */}
        {hasAiResult ? (
          <button
            type="button"
            onClick={handleScaffold}
            disabled={!screenId.trim() || loading}
            className="flex items-center gap-2 px-7 py-3 rounded-xl text-sm font-bold transition-all"
            style={{
              background: !screenId.trim() || loading ? '#2a2a2a' : '#f4821f',
              color: !screenId.trim() || loading ? '#555555' : '#ffffff',
              cursor: !screenId.trim() || loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? (
              <>
                <svg className="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                생성 중...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[18px]">draw</span>
                AI 설계
              </>
            )}
          </button>
        ) : (
          /* Phase 1: AI 자동생성 버튼 (하단 보조) */
          <button
            type="button"
            onClick={handleAiGenerate}
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
                AI 생성 중...
              </>
            ) : (
              <>
                <span style={{ fontSize: 16 }}>⚡</span>
                AI 자동생성
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}
