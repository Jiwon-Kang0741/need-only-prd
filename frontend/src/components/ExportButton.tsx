import { exportSpec } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

export default function ExportButton() {
  const specMarkdown = useSessionStore((s) => s.specMarkdown)
  const disabled = !specMarkdown

  return (
    <button
      onClick={exportSpec}
      disabled={disabled}
      className="bg-secondary-container text-on-secondary-container px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <span className="material-symbols-outlined text-[18px]">download</span>
      download.md
    </button>
  )
}
