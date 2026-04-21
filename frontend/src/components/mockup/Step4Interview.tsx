import { useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'
import type { InterviewQuestion } from '../../types'

type AnswerMode = 'questions' | 'raw'

const PRIORITY_COLORS: Record<string, string> = {
  '높음': 'bg-error-container text-on-error-container',
  '보통': 'bg-secondary-container text-on-secondary-container',
  '낮음': 'bg-surface-container-high text-on-surface-variant',
}

export default function Step4Interview() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const aiInterview = useSessionStore((s) => s.mockupAiInterview)
  const submitResult = useSessionStore((s) => s.mockupSubmitInterviewResult)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const questions = mockupState?.interviewQuestions ?? null
  const [answerMode, setAnswerMode] = useState<AnswerMode>('questions')
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [rawText, setRawText] = useState('')

  function updateAnswer(no: number, value: string) {
    setAnswers((prev) => ({ ...prev, [no]: value }))
  }

  async function handleSubmit() {
    if (loading) return
    if (answerMode === 'questions' && questions) {
      const formatted = questions
        .map((q) => ({ no: q.no, answer: answers[q.no]?.trim() || '' }))
        .filter((a) => a.answer.length > 0)
      if (formatted.length === 0) return
      await submitResult(formatted, undefined)
    } else {
      if (!rawText.trim()) return
      await submitResult(undefined, rawText.trim())
    }
  }

  const hasAnswers =
    answerMode === 'questions'
      ? Object.values(answers).some((a) => a.trim().length > 0)
      : rawText.trim().length > 0

  return (
    <div className="space-y-6">
      {/* Generate questions */}
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-5">
        <h3 className="text-lg font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">forum</span>
          인터뷰 질문 생성
        </h3>

        {error && (
          <div className="text-sm text-error bg-error-container/30 px-4 py-2 rounded-lg">
            {error}
          </div>
        )}

        {!questions && (
          <div className="flex items-center gap-3 flex-wrap">
            <button
              type="button"
              onClick={aiInterview}
              disabled={loading}
              className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {loading ? (
                <>
                  <svg className="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  질문 생성 중...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined">psychology</span>
                  인터뷰 질문 자동 생성
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => goToStep(6)}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-3 rounded-xl font-bold font-headline transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#888888',
              }}
            >
              <span className="material-symbols-outlined text-[18px]">skip_next</span>
              인터뷰 건너뛰기
            </button>
          </div>
        )}
      </div>

      {/* Answer section */}
      {questions && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-5">
          {/* Mode tabs */}
          <div className="flex gap-1 p-1 bg-surface-container rounded-lg w-fit">
            <button
              type="button"
              onClick={() => setAnswerMode('questions')}
              className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${
                answerMode === 'questions'
                  ? 'bg-primary text-on-primary shadow-sm'
                  : 'text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              질문별 답변
            </button>
            <button
              type="button"
              onClick={() => setAnswerMode('raw')}
              className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${
                answerMode === 'raw'
                  ? 'bg-primary text-on-primary shadow-sm'
                  : 'text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              인터뷰 전문 붙여넣기
            </button>
          </div>

          {answerMode === 'questions' ? (
            <div className="space-y-4">
              {questions.map((q: InterviewQuestion) => (
                <div
                  key={q.no}
                  className="border border-outline-variant rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2 flex-1">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary text-on-primary text-xs font-bold shrink-0 mt-0.5">
                        {q.no}
                      </span>
                      <span className="text-sm font-semibold text-on-surface leading-relaxed">
                        {q.question}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-tertiary-fixed text-on-tertiary-fixed">
                        {q.category}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${PRIORITY_COLORS[q.priority] ?? PRIORITY_COLORS['보통']}`}>
                        {q.priority}
                      </span>
                    </div>
                  </div>
                  {q.tip && (
                    <p className="text-xs text-on-surface-variant pl-8">
                      <span className="material-symbols-outlined text-[14px] align-middle mr-1">lightbulb</span>
                      {q.tip}
                    </p>
                  )}
                  <textarea
                    value={answers[q.no] ?? ''}
                    onChange={(e) => updateAnswer(q.no, e.target.value)}
                    placeholder="답변을 입력하세요..."
                    className="w-full min-h-[60px] px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface text-sm focus:border-primary focus:ring-1 focus:ring-primary transition-colors resize-y"
                    disabled={loading}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              <label className="text-sm font-semibold text-on-surface-variant">
                인터뷰 내용을 그대로 붙여넣으세요
              </label>
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="인터뷰 전문을 여기에 붙여넣으세요..."
                className="w-full min-h-[300px] px-4 py-3 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface text-sm focus:border-primary focus:ring-1 focus:ring-primary transition-colors resize-y"
                disabled={loading}
              />
            </div>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!hasAnswers || loading}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {loading ? (
              <>
                <svg className="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                처리 중...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined">send</span>
                답변 완료
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}
