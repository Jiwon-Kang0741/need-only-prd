import { useState } from 'react'
import { importSpec } from '../../api/client'
import { useSessionStore } from '../../store/sessionStore'

const PFY_MOCKUP_BUILDER_URL = 'http://localhost:8081/mockup/builder'

export default function MockupPipeline() {
  const setSpecMarkdown = useSessionStore((s) => s.setSpecMarkdown)
  const setSpecVersion = useSessionStore((s) => s.setSpecVersion)

  const [specText, setSpecText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleImport() {
    if (!specText.trim() || loading) return
    setLoading(true)
    setError(null)
    try {
      const result = await importSpec(specText)
      setSpecMarkdown(specText.trim())
      setSpecVersion(result.spec_version)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const content = ev.target?.result
      if (typeof content === 'string') setSpecText(content)
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  return (
    <div className="max-w-[1400px] mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold font-headline text-on-surface mb-1">MockUp Builder</h1>
        <p className="text-sm text-on-surface-variant">
          원본 pfy-front의 MockupBuilder를 그대로 사용합니다. 화면 스펙 정의 → Vue 생성 → 주석 →
          인터뷰 → spec.md 까지 아래 iframe 안에서 진행한 뒤, 최종 spec.md를 우리 세션으로 불러오세요.
        </p>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-surface-container">
          <h2 className="font-bold text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-tertiary">dashboard_customize</span>
            원본 MockupBuilder
          </h2>
          <a
            href={PFY_MOCKUP_BUILDER_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[16px]">open_in_new</span>
            새 탭에서 열기
          </a>
        </div>
        <iframe
          src={PFY_MOCKUP_BUILDER_URL}
          className="w-full border-0 bg-white"
          style={{ height: '900px' }}
          title="pfy-front MockupBuilder"
        />
        <div className="px-4 py-2 bg-surface-container-low text-xs text-on-surface-variant border-t border-surface-container">
          서버 필요: <code className="bg-surface-container px-1 rounded">pfy-front Vue :8081</code>,{' '}
          <code className="bg-surface-container px-1 rounded">scaffolding Express :4000</code>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-4">
        <div>
          <h2 className="text-xl font-bold font-headline text-on-surface mb-1 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">upload</span>
            Spec.md 불러오기
          </h2>
          <p className="text-sm text-on-surface-variant">
            MockupBuilder에서 완성된 spec.md 내용을 붙여넣거나 파일로 업로드하면, 이후 Chat 리파인·
            코드 생성에 사용됩니다.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="bg-surface-container text-on-surface hover:bg-surface-container-high px-3 py-1.5 rounded-lg cursor-pointer text-sm flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[18px]">upload_file</span>
            파일 선택
            <input type="file" accept=".md,.txt" onChange={handleFileUpload} className="hidden" />
          </label>
          <span className="text-xs text-on-surface-variant">또는 아래 textarea에 직접 붙여넣기</span>
        </div>

        <textarea
          value={specText}
          onChange={(e) => setSpecText(e.target.value)}
          rows={12}
          placeholder="spec.md 전체 내용을 붙여넣으세요..."
          className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={loading}
        />

        {error && (
          <div className="bg-error-container text-on-error-container px-4 py-2 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleImport}
            disabled={!specText.trim() || loading}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? '불러오는 중...' : 'Spec.md 불러오기 → 코드 생성으로 이동'}
            {!loading && <span className="material-symbols-outlined">arrow_forward</span>}
          </button>
        </div>
      </div>
    </div>
  )
}
