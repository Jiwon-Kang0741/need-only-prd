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
    <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/15 flex flex-col h-[500px]">
      <div className="p-4 border-b border-outline-variant/15 bg-surface-container-low/50">
        <h2 className="font-headline font-bold text-base text-on-surface">Refine Spec</h2>
        <p className="text-[10px] text-on-secondary-container font-semibold uppercase tracking-widest mt-0.5">
          Ask questions or request changes
        </p>
      </div>

      <div className="flex-1 p-6 overflow-y-auto space-y-6 no-scrollbar">
        {chatMessages.length === 0 && !isGenerating && (
          <p className="text-sm text-outline text-center mt-8">
            Send a message to refine your spec.
          </p>
        )}
        {chatMessages.map((msg, i) => (
          <ChatMessageBubble key={i} message={msg} />
        ))}
        {isGenerating && (
          <div className="flex items-center gap-2 px-4 py-2 bg-surface-container-high rounded-full w-fit">
            <span className="w-1.5 h-1.5 bg-secondary rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-secondary rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-secondary rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 bg-surface-container-low border-t border-outline-variant/15">
        <div className="flex items-end gap-3 bg-surface-container-lowest rounded-xl p-2 shadow-inner border border-outline-variant/10">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isGenerating}
            placeholder="Ask to refine the spec... (Enter to send)"
            rows={2}
            className="flex-1 bg-transparent border-none focus:ring-0 text-sm py-2 px-2 resize-none placeholder:text-outline/40 text-on-surface"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isGenerating}
            className="bg-primary text-on-primary w-10 h-10 rounded-lg flex items-center justify-center hover:shadow-lg active:scale-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-symbols-outlined">send</span>
          </button>
        </div>
      </div>
    </div>
  )
}
