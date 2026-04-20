import { useEffect, useRef, useState } from 'react'
import { getSessionId } from '../../api/client'
import { useSessionStore } from '../../store/sessionStore'

const PFY_BASE_URL = 'http://localhost:8085'
const PFY_MOCKUP_BUILDER_URL = `${PFY_BASE_URL}/mockup/builder`
const VIEWPORT_WIDTH = 1600
const VIEWPORT_HEIGHT = 1000

interface PfyPageGeneratedMessage {
  type: 'pfy-page-generated'
  routePath: string
  previewUrl: string
  pageName: string
}

interface PfyInterviewResultMessage {
  type: 'pfy-interview-result-success'
  screenName: string
  pageName: string
  title: string
  pageType: string
}

type PfyMessage = PfyPageGeneratedMessage | PfyInterviewResultMessage

function isPfyMessage(data: unknown): data is PfyMessage {
  if (typeof data !== 'object' || data === null) return false
  const t = (data as { type?: string }).type
  return t === 'pfy-page-generated' || t === 'pfy-interview-result-success'
}

export default function MockupPipeline() {
  const setSpecMarkdown = useSessionStore((s) => s.setSpecMarkdown)
  const setSpecVersion = useSessionStore((s) => s.setSpecVersion)
  const setStatus = useSessionStore((s) => s.setStatus)
  const setGenerating = useSessionStore((s) => s.setGenerating)

  const [error, setError] = useState<string | null>(null)
  const [iframeUrl, setIframeUrl] = useState(PFY_MOCKUP_BUILDER_URL)
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const update = () => {
      const next = Math.min(el.clientWidth / VIEWPORT_WIDTH, 1)
      setScale((prev) => (Math.abs(prev - next) < 0.005 ? prev : next))
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    async function handleMessage(event: MessageEvent) {
      if (!isPfyMessage(event.data)) return

      if (event.data.type === 'pfy-page-generated') {
        setIframeUrl(`${PFY_BASE_URL}${event.data.routePath}`)
        return
      }

      const payload = event.data
      setGenerating(true)
      setStatus('인터뷰 결과를 spec.md로 변환 중...')
      setError(null)

      try {
        const res = await fetch('/api/mockup/generate-spec-from-builder', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': getSessionId(),
          },
          body: JSON.stringify({
            screen_name: payload.screenName,
            page_name: payload.pageName,
            title: payload.title,
            page_type: payload.pageType,
          }),
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
          throw new Error(err.detail ?? `Request failed: ${res.status}`)
        }
        const data = (await res.json()) as { spec_markdown: string; spec_version: number }
        setSpecMarkdown(data.spec_markdown)
        setSpecVersion(data.spec_version)
        setStatus(null)
        setGenerating(false)
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e))
        setStatus(null)
        setGenerating(false)
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [setSpecMarkdown, setSpecVersion, setStatus, setGenerating])

  return (
    <div className="fixed inset-0 top-[64px] flex flex-col bg-surface z-10">
      {error && (
        <div className="bg-error-container text-on-error-container px-6 py-3 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-4 text-xs underline">
            닫기
          </button>
        </div>
      )}
      <div ref={containerRef} className="relative flex-1 overflow-auto bg-white">
        <iframe
          src={iframeUrl}
          className="border-0 bg-white"
          style={{
            width: `${VIEWPORT_WIDTH}px`,
            height: `${VIEWPORT_HEIGHT}px`,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
          }}
          title="pfy-front MockupBuilder"
        />
        <div className="fixed bottom-2 right-3 bg-black/60 text-white text-xs px-2 py-1 rounded-md pointer-events-none">
          {Math.round(scale * 100)}%
        </div>
      </div>
    </div>
  )
}
