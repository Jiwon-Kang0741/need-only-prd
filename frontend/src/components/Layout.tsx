import type { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
  onNewSession?: () => void
}

export default function Layout({ children, onNewSession }: LayoutProps) {
  return (
    <div className="min-h-screen bg-surface">
      <header className="bg-surface sticky top-0 z-50 flex items-center justify-between px-6 py-4">
        <h1 className="text-xl font-bold tracking-tight font-headline text-on-surface">
          Need Only PRD
        </h1>
        {onNewSession && (
          <button
            onClick={onNewSession}
            className="gradient-button text-on-primary px-5 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all"
          >
            <span className="material-symbols-outlined text-sm">add</span>
            New Session
          </button>
        )}
      </header>
      <main className="p-6">{children}</main>
    </div>
  )
}
