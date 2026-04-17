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

    // If mockup pipeline is in progress, confirm before switching
    const mockupInProgress = mockupState !== null || mockupLoading
    if (specMode === 'mockup' && mockupInProgress && mode === 'text') {
      setPendingMode(mode)
      setShowConfirm(true)
      return
    }

    setSpecMode(mode)
  }

  function confirmSwitch() {
    if (pendingMode) {
      setSpecMode(pendingMode)
    }
    setShowConfirm(false)
    setPendingMode(null)
  }

  function cancelSwitch() {
    setShowConfirm(false)
    setPendingMode(null)
  }

  return (
    <div className="py-6 px-4">
      {/* Tab bar */}
      <div className="flex justify-center mb-8">
        <div className="flex gap-1 p-1 bg-surface-container rounded-xl">
          {TABS.map((tab) => (
            <button
              key={tab.mode}
              type="button"
              onClick={() => handleTabClick(tab.mode)}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-lg text-sm font-bold transition-all ${
                specMode === tab.mode
                  ? 'bg-primary text-on-primary shadow-md'
                  : 'text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {specMode === 'text' ? <InputPanel /> : <MockupPipeline />}

      {/* Confirmation dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-on-surface/40 backdrop-blur-sm">
          <div className="bg-surface-container-lowest rounded-2xl shadow-2xl px-8 py-6 max-w-sm mx-4 space-y-4">
            <h3 className="text-lg font-bold font-headline text-on-surface">모드 전환</h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Mockup 파이프라인이 진행 중입니다. 텍스트 입력 모드로 전환하면 현재 진행 상태가 유지됩니다. 전환하시겠습니까?
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={cancelSwitch}
                className="px-4 py-2 rounded-lg text-sm font-bold text-on-surface-variant hover:bg-surface-container-high transition-colors"
              >
                취소
              </button>
              <button
                type="button"
                onClick={confirmSwitch}
                className="px-4 py-2 rounded-lg text-sm font-bold bg-primary text-on-primary hover:bg-primary-container transition-colors"
              >
                전환
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
