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

      setStatus('Analyzing requirements...')
      generateSpec((event: SSEEvent) => {
        if (event.type === 'status' && event.message) {
          setStatus(event.message)
        } else if (event.type === 'text' && event.content) {
          appendSpecChunk(event.content)
        } else if (event.type === 'complete') {
          setStatus(null)
          setGenerating(false)
        } else if (event.type === 'error') {
          setStatus(event.message ?? 'An error occurred')
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
    <div className="max-w-3xl mx-auto">
      <div className="bg-white rounded-lg border shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Input</h2>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
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

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste your meeting notes, emails, or chat logs here..."
          className="w-full rounded-md border border-gray-300 p-3 text-sm text-gray-800 placeholder-gray-400 resize-y focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          style={{ minHeight: '300px' }}
          disabled={isGenerating}
        />

        <div className="flex items-center justify-between">
          <span
            className={`text-xs ${
              isOverLimit
                ? 'text-red-600 font-semibold'
                : isNearLimit
                ? 'text-amber-600'
                : 'text-gray-400'
            }`}
          >
            {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters
            {isOverLimit && ' — over limit'}
          </span>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!text.trim() || isGenerating || isOverLimit}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isGenerating ? 'Generating...' : 'Generate Spec'}
          </button>
        </div>
      </div>
    </div>
  )
}
