import type { ChatMessage } from '../types'

interface ChatMessageProps {
  message: ChatMessage
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-0`}>
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[85%]`}>
        <div
          className={`p-4 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words ${
            isUser
              ? 'bg-primary-container text-on-primary-container rounded-br-none shadow-sm'
              : 'bg-surface-container-high text-on-surface rounded-bl-none'
          }`}
        >
          {message.content}
        </div>
        <span className={`text-[10px] text-outline mt-1 ${isUser ? 'mr-1' : 'ml-1'}`}>
          {formatTimestamp(message.timestamp)}
        </span>
      </div>
    </div>
  )
}
