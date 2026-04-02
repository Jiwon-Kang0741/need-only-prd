import { exportSpec } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

export default function ExportButton() {
  const specMarkdown = useSessionStore((s) => s.specMarkdown)
  const disabled = !specMarkdown

  return (
    <button
      onClick={exportSpec}
      disabled={disabled}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
        disabled
          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
          : 'bg-green-600 text-white hover:bg-green-700'
      }`}
    >
      <span>⬇</span>
      Download spec.md
    </button>
  )
}
