import { useState } from 'react'
import { useSessionStore } from '../store/sessionStore'
import InputPanel from './InputPanel'
import MockupPipeline from './mockup/MockupPipeline'

const TABS = [
  { mode: 'text' as const, label: '텍스트 입력', icon: 'description' },
  { mode: 'mockup' as const, label: 'Mockup 생성', icon: 'devices' },
]

export default function SpecModeSelector() {
  const specMode = useSessionStore((s) => s.specMode)
  const setSpecMode = useSessionStore((s) => s.setSpecMode)
  const mockupState = useSessionStore((s) => s.mockupState)
  const mockupLoading = useSessionStore((s) => s.mockupLoading)
  const [showConfirm, setShowConfirm] = useState(false)
  const [pendingMode, setPendingMode] = useState<'text' | 'mockup' | null>(null)

  function handleTabClick(mode: 'text' | 'mockup') {
    if (mode === specMode) return
    const mockupInProgress = mockupState !== null || mockupLoading
    if (specMode === 'mockup' && mockupInProgress && mode === 'text') {
      setPendingMode(mode)
      setShowConfirm(true)
      return
    }
    setSpecMode(mode)
  }

  function confirmSwitch() {
    if (pendingMode) setSpecMode(pendingMode)
    setShowConfirm(false)
    setPendingMode(null)
  }

  function cancelSwitch() {
    setShowConfirm(false)
    setPendingMode(null)
  }

  if (specMode === 'mockup') {
    return (
      <div className="flex flex-col" style={{ background: '#0f0f0f' }}>
        {/* Mode tabs (above mockup pipeline) */}
        <div
          className="flex items-center gap-1 px-6 py-2"
          style={{ borderBottom: '1px solid #1e1e1e' }}
        >
          {TABS.map((tab) => {
            const isActive = specMode === tab.mode
            return (
              <button
                key={tab.mode}
                type="button"
                onClick={() => handleTabClick(tab.mode)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition-all"
                style={{
                  background: isActive ? 'rgba(244,130,31,0.12)' : 'transparent',
                  color: isActive ? '#f4821f' : '#666666',
                  border: isActive ? '1px solid rgba(244,130,31,0.25)' : '1px solid transparent',
                }}
              >
                <span className="material-symbols-outlined text-[17px]">{tab.icon}</span>
                {tab.label}
              </button>
            )
          })}
        </div>
        <MockupPipeline />
        {showConfirm && <ConfirmDialog onConfirm={confirmSwitch} onCancel={cancelSwitch} />}
      </div>
    )
  }

  return (
    <div style={{ background: '#0f0f0f', minHeight: '100%' }}>
      {/* Mode tabs */}
      <div
        className="flex items-center gap-1 px-6 py-2"
        style={{ borderBottom: '1px solid #1e1e1e' }}
      >
        {TABS.map((tab) => {
          const isActive = specMode === tab.mode
          return (
            <button
              key={tab.mode}
              type="button"
              onClick={() => handleTabClick(tab.mode)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition-all"
              style={{
                background: isActive ? 'rgba(244,130,31,0.12)' : 'transparent',
                color: isActive ? '#f4821f' : '#666666',
                border: isActive ? '1px solid rgba(244,130,31,0.25)' : '1px solid transparent',
              }}
            >
              <span className="material-symbols-outlined text-[17px]">{tab.icon}</span>
              {tab.label}
            </button>
          )
        })}
      </div>

      <div className="py-6 px-4">
        <InputPanel />
      </div>

      {showConfirm && <ConfirmDialog onConfirm={confirmSwitch} onCancel={cancelSwitch} />}
    </div>
  )
}

function ConfirmDialog({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}>
      <div
        className="rounded-2xl shadow-2xl px-8 py-6 max-w-sm mx-4 space-y-4"
        style={{ background: '#1a1a1a', border: '1px solid #2a2a2a' }}
      >
        <h3 className="text-lg font-bold text-white" style={{ fontFamily: 'Manrope, sans-serif' }}>모드 전환</h3>
        <p className="text-sm leading-relaxed" style={{ color: '#888888' }}>
          Mockup 파이프라인이 진행 중입니다. 텍스트 입력 모드로 전환하면 현재 진행 상태가 유지됩니다. 전환하시겠습니까?
        </p>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm font-bold transition-colors"
            style={{ background: '#252525', color: '#888888' }}
          >
            취소
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="px-4 py-2 rounded-lg text-sm font-bold transition-colors"
            style={{ background: '#f4821f', color: '#ffffff' }}
          >
            전환
          </button>
        </div>
      </div>
    </div>
  )
}
