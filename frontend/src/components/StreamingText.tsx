interface StreamingTextProps {
  text: string
  isStreaming: boolean
}

export default function StreamingText({ text, isStreaming }: StreamingTextProps) {
  return (
    <span>
      {text}
      {isStreaming && (
        <span
          className="inline-block w-0.5 h-4 bg-gray-700 ml-0.5 align-middle animate-blink"
          aria-hidden="true"
        />
      )}
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        .animate-blink {
          animation: blink 1s step-end infinite;
        }
      `}</style>
    </span>
  )
}
