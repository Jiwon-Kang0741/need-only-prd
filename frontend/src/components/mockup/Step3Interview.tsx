import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useSessionStore } from '../../store/sessionStore'

export default function Step3Interview() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const parseInterview = useSessionStore((s) => s.mockupParseInterview)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const [rawText, setRawText] = useState(mockupState?.rawInterviewText ?? '')

  const canSubmit = rawText.trim().length > 0 && !loading
  const hasNotes = !!mockupState?.interviewNotesMd

  async function handleSubmit() {
    if (!canSubmit) return
    await parseInterview(rawText)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold font-headline text-on-surface mb-1">③ 인터뷰</h2>
        <p className="text-sm text-on-surface-variant">
          고객과 Mockup을 보며 진행한 인터뷰 원문(녹취 풀이 / 회의록)을 붙여넣으세요.
          LLM이 Keep / Change / Add / Out / TBD 5개 섹션으로 정리합니다.
        </p>
      </div>

      <div>
        <label className="text-sm font-bold text-on-surface mb-1 block">인터뷰 원문 *</label>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          rows={15}
          placeholder="녹취를 풀어 정리한 텍스트 또는 회의록 원문을 붙여넣으세요..."
          className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={loading}
        />
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold flex items-center gap-2 disabled:opacity-50"
        >
          {loading ? 'InterviewNote 생성 중...' : 'InterviewNote 생성'}
        </button>
        {hasNotes && (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-surface-container text-on-surface hover:bg-surface-container-high disabled:opacity-50"
          >
            재생성
          </button>
        )}
      </div>

      {error && (
        <div className="bg-error-container text-on-error-container px-4 py-2 rounded-lg text-sm">{error}</div>
      )}

      {hasNotes && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
          <h3 className="font-bold text-on-surface mb-3">InterviewNote.md</h3>
          <div className="prose prose-sm max-w-none text-on-surface">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {mockupState?.interviewNotesMd ?? ''}
            </ReactMarkdown>
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => goToStep(2)}
          className="text-on-surface-variant hover:text-on-surface px-4 py-2 rounded-lg hover:bg-surface-container"
        >
          ← 이전
        </button>
        {hasNotes && (
          <button
            type="button"
            onClick={() => goToStep(4)}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold flex items-center gap-2"
          >
            다음: Spec 생성 →
          </button>
        )}
      </div>
    </div>
  )
}
