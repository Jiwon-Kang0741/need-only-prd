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
          className="inline-block w-0.5 h-4 bg-primary ml-0.5 align-middle animate-blink"
          aria-hidden="true"
        />
      )}
    </span>
  )
}
