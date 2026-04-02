import type { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
  onNewSession?: () => void
}

export default function Layout({ children, onNewSession }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 shadow-sm flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Need Only PRD</h1>
          <p className="text-sm text-gray-500">
            Transform unstructured text into AI-ready technical specifications
          </p>
        </div>
        {onNewSession && (
          <button
            onClick={onNewSession}
            className="px-4 py-2 rounded-md text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
          >
            New Session
          </button>
        )}
      </header>
      <main className="p-6">{children}</main>
    </div>
  )
}
