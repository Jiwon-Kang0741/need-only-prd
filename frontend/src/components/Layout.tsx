import type { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
  onNewSession?: () => void
}

const NAV_TABS = [
  { label: 'Dashboard', active: true },
  { label: 'Projects', active: false },
  { label: 'Templates', active: false },
  { label: 'Resources', active: false },
]

export default function Layout({ children, onNewSession }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#0f0f0f' }}>
      {/* ── Top Header ── */}
      <header
        className="flex items-center justify-between px-6 py-3 sticky top-0 z-50"
        style={{ background: '#0f0f0f', borderBottom: '1px solid #1e1e1e' }}
      >
        {/* Logo */}
        <div className="flex items-center">
          <img
            src="/hanwha-systems.png"
            alt="Hanwha Systems"
            style={{ height: '32px', width: 'auto' }}
          />
        </div>

        {/* Tab nav */}
        <nav className="flex items-center gap-1">
          {NAV_TABS.map((tab) => (
            <button
              key={tab.label}
              type="button"
              className="px-4 py-2 text-sm font-medium transition-colors relative"
              style={{
                color: tab.active ? '#f4821f' : '#666666',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              {tab.label}
              {tab.active && (
                <span
                  className="absolute bottom-0 left-4 right-4 h-0.5 rounded-full"
                  style={{ background: '#f4821f' }}
                />
              )}
            </button>
          ))}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors"
            style={{ color: '#888888', background: 'none' }}
          >
            <span className="material-symbols-outlined text-[20px]">notifications</span>
          </button>
          <button
            type="button"
            className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors"
            style={{ color: '#888888', background: 'none' }}
          >
            <span className="material-symbols-outlined text-[20px]">settings</span>
          </button>
          <button
            type="button"
            onClick={onNewSession}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-colors"
            style={{ background: '#f4821f', color: '#ffffff' }}
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Create New
          </button>
        </div>
      </header>

      {/* ── Body ── */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  )
}
