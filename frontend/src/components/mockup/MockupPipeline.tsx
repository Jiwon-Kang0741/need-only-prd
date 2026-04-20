import { useEffect, useRef, useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'

const PFY_BASE_URL = 'http://localhost:8081'
const PFY_MOCKUP_BUILDER_URL = `${PFY_BASE_URL}/mockup/builder`

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

function getSessionId(): string {
  let id = sessionStorage.getItem('session_id')
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem('session_id', id)
  }
  return id
}

export default function MockupPipeline() {
  const setSpecMarkdown = useSessionStore((s) => s.setSpecMarkdown)
  const setSpecVersion = useSessionStore((s) => s.setSpecVersion)
  const setStatus = useSessionStore((s) => s.setStatus)
  const setGenerating = useSessionStore((s) => s.setGenerating)

  const [error, setError] = useState<string | null>(null)
  const [iframeUrl, setIframeUrl] = useState(PFY_MOCKUP_BUILDER_URL)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    async function handleMessage(event: MessageEvent) {
      console.log('[MockupPipeline] postMessage received:', event.data, 'from:', event.origin)
      if (!isPfyMessage(event.data)) {
        console.log('[MockupPipeline] not a pfy message, ignoring')
        return
      }

      if (event.data.type === 'pfy-page-generated') {
        console.log('[MockupPipeline] page-generated → switching iframe to', event.data.routePath)
        setIframeUrl(`${PFY_BASE_URL}${event.data.routePath}`)
        return
      }

      // pfy-interview-result-success: 인터뷰 완료 → spec.md 생성
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
      <iframe
        ref={iframeRef}
        src={iframeUrl}
        className="flex-1 border-0 bg-white w-full"
        title="pfy-front MockupBuilder"
      />
    </div>
  )
}
