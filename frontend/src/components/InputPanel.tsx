import { useRef, useState } from 'react'
import { submitInput, generateSpec } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import type { SSEEvent } from '../types'

const MAX_CHARS = 50000
const WARN_THRESHOLD = 45000

export default function InputPanel() {
  const [text, setText] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const isGenerating = useSessionStore((s) => s.isGenerating)
  const setGenerating = useSessionStore((s) => s.setGenerating)
  const setStatus = useSessionStore((s) => s.setStatus)
  const appendSpecChunk = useSessionStore((s) => s.appendSpecChunk)
  const setSpecMarkdown = useSessionStore((s) => s.setSpecMarkdown)
  const setRawInput = useSessionStore((s) => s.setRawInput)

  const charCount = text.length
  const isOverLimit = charCount > MAX_CHARS
  const isNearLimit = charCount >= WARN_THRESHOLD

  async function handleSubmit() {
    if (!text.trim() || isGenerating || isOverLimit) return

    setGenerating(true)
    setStatus('Submitting input...')
    setSpecMarkdown(null)

    try {
      const res = await submitInput(text)
      if (!res.ok) throw new Error(`Submit failed: ${res.status}`)

      setRawInput(text)
      setStatus('Analyzing requirements...')
      generateSpec((event: SSEEvent) => {
        if (event.type === 'status') {
          setStatus(event.content ?? event.message ?? null)
        } else if ((event.type === 'chunk' || event.type === 'text') && event.content) {
          appendSpecChunk(event.content)
        } else if (event.type === 'complete') {
          setStatus(null)
          setGenerating(false)
        } else if (event.type === 'error') {
          setStatus(event.content ?? event.message ?? 'An error occurred')
          setGenerating(false)
        }
      })
    } catch (err) {
      setStatus(err instanceof Error ? err.message : 'Failed to submit')
      setGenerating(false)
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const content = ev.target?.result
      if (typeof content === 'string') setText(content)
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  return (
    <div className="max-w-[768px] mx-auto space-y-8">
      {/* Hero header */}
      <div className="flex flex-col items-center text-center space-y-3 mb-4">
        <h1 className="text-[3.5rem] leading-tight font-extrabold font-headline tracking-tighter text-on-background">
          Input
        </h1>
        <p className="text-secondary max-w-md">
          Transform fragmented notes into precise architectural specifications.
        </p>
      </div>

      {/* Input card */}
      <div className="bg-surface-container-lowest rounded-xl p-1 shadow-[0_12px_32px_-4px_rgba(25,28,30,0.06)]">
        {/* Card header */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-surface-container">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">description</span>
            <span className="text-xs font-bold text-on-surface-variant tracking-widest uppercase">
              Source Material
            </span>
          </div>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="text-primary hover:text-primary-container flex items-center gap-1.5 text-sm font-semibold"
          >
            <span className="material-symbols-outlined text-[20px]">upload_file</span>
            Upload file
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {/* Textarea */}
        <div className="p-1">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste your meeting notes, emails, or chat logs here..."
            className="w-full min-h-[400px] p-6 text-on-surface bg-surface-container-lowest border-none focus:ring-0 resize-y placeholder:text-outline/40 leading-relaxed"
            style={{ minHeight: '400px' }}
            disabled={isGenerating}
          />
        </div>

        {/* Card footer */}
        <div className="px-6 py-4 bg-surface-container-low/50 rounded-b-xl flex justify-between items-center border-t border-surface-container">
          <div className="flex items-center gap-3">
            <div className="flex h-1.5 w-32 bg-surface-container rounded-full overflow-hidden">
              <div
                className={`${isOverLimit ? 'bg-error' : 'bg-primary'} rounded-full transition-all`}
                style={{ width: `${Math.min(charCount / MAX_CHARS * 100, 100)}%` }}
              />
            </div>
            <span
              className={`text-xs font-medium ${
                isOverLimit
                  ? 'text-error'
                  : isNearLimit
                  ? 'text-amber-600'
                  : 'text-on-secondary-container'
              }`}
            >
              {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()}
              {isOverLimit && ' — over limit'}
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-tertiary-fixed text-on-tertiary-fixed">
            <span className="material-symbols-outlined text-[16px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              auto_awesome
            </span>
            <span className="text-[10px] font-bold uppercase tracking-wider">AI Ready</span>
          </div>
        </div>
      </div>

      {/* Generate button */}
      <div className="flex flex-col items-center gap-4">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!text.trim() || isGenerating || isOverLimit}
          className="gradient-button text-on-primary w-full md:w-auto min-w-[240px] px-8 py-4 rounded-xl font-bold font-headline text-lg shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          {isGenerating ? 'Generating...' : 'Generate Spec'}
          {!isGenerating && (
            <span className="material-symbols-outlined">arrow_forward</span>
          )}
        </button>
        <span className="text-xs text-secondary/60 flex items-center gap-1">
          <span className="material-symbols-outlined text-[14px]">lock</span>
          Your data stays private and is never stored
        </span>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
        <div className="p-6 bg-surface-container-low rounded-xl flex flex-col gap-3">
          <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center shadow-sm">
            <span className="material-symbols-outlined text-primary">psychology</span>
          </div>
          <span className="font-bold font-headline text-on-surface">AI Extraction</span>
          <p className="text-sm text-on-secondary-container leading-relaxed">
            Automatically identifies stakeholders, goals, and constraints from messy text.
          </p>
        </div>
        <div className="p-6 bg-surface-container-low rounded-xl flex flex-col gap-3">
          <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center shadow-sm">
            <span className="material-symbols-outlined text-primary">architecture</span>
          </div>
          <span className="font-bold font-headline text-on-surface">Structured Output</span>
          <p className="text-sm text-on-secondary-container leading-relaxed">
            Formats your ideas into professional PRD sections with technical precision.
          </p>
        </div>
        <div className="p-6 bg-surface-container-low rounded-xl flex flex-col gap-3">
          <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center shadow-sm">
            <span className="material-symbols-outlined text-primary">history_edu</span>
          </div>
          <span className="font-bold font-headline text-on-surface">Smart Context</span>
          <p className="text-sm text-on-secondary-container leading-relaxed">
            Understands industry standards to suggest missing functional requirements.
          </p>
        </div>
      </div>
    </div>
  )
}
