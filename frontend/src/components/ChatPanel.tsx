import { useEffect, useRef, useState } from 'react'
import { useSessionStore } from '../store/sessionStore'
import ChatMessageBubble from './ChatMessage'

export default function ChatPanel() {
  const chatMessages = useSessionStore((s) => s.chatMessages)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const sendChatMessage = useSessionStore((s) => s.sendChatMessage)

  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, isGenerating])

  function handleSend() {
    const trimmed = input.trim()
    if (!trimmed || isGenerating) return
    setInput('')
    sendChatMessage(trimmed)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="bg-white rounded-lg border shadow-sm flex flex-col h-full" style={{ minHeight: '60vh' }}>
      <div className="px-4 py-3 border-b">
        <h2 className="text-base font-semibold text-gray-800">Refine Spec</h2>
        <p className="text-xs text-gray-500 mt-0.5">Ask questions or request changes</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-1" style={{ maxHeight: '55vh' }}>
        {chatMessages.length === 0 && !isGenerating && (
          <p className="text-sm text-gray-400 text-center mt-8">
            Send a message to refine your spec.
          </p>
        )}
        {chatMessages.map((msg, i) => (
          <ChatMessageBubble key={i} message={msg} />
        ))}
        {isGenerating && (
          <div className="flex justify-start mb-3">
            <div className="bg-gray-100 text-gray-500 px-4 py-2 rounded-2xl rounded-bl-sm text-sm flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t px-4 py-3 flex gap-2 items-end">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isGenerating}
          placeholder="Ask to refine the spec... (Enter to send)"
          rows={2}
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isGenerating}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors self-end ${
            !input.trim() || isGenerating
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          Send
        </button>
      </div>
    </div>
  )
}
