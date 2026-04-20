import type { SessionState, SSEEvent, ValidationResult } from '../types'

export function getSessionId(): string {
  let id = sessionStorage.getItem('session_id')
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem('session_id', id)
  }
  return id
}

function apiHeaders(): Record<string, string> {
  return { 'X-Session-ID': getSessionId() }
}

export async function submitInput(text: string): Promise<Response> {
  return fetch('/api/input', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
}

export async function uploadFile(file: File): Promise<Response> {
  const form = new FormData()
  form.append('file', file)
  return fetch('/api/upload', {
    method: 'POST',
    headers: apiHeaders(),
    body: form,
  })
}

function parseSSELine(line: string): SSEEvent | null {
  if (!line.startsWith('data: ')) return null
  try {
    return JSON.parse(line.slice(6)) as SSEEvent
  } catch {
    return null
  }
}

async function consumeSSE(
  url: string,
  onEvent: (event: SSEEvent) => void,
  body?: object,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(url, {
      method: body ? 'POST' : 'GET',
      headers: { ...apiHeaders(), ...(body ? { 'Content-Type': 'application/json' } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
      signal,
    })
  } catch (err) {
    if (signal?.aborted) return
    onEvent({ type: 'error', content: err instanceof Error ? err.message : 'Network error' })
    return
  }

  if (!response.ok) {
    const errData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    onEvent({ type: 'error', content: errData.detail ?? `Request failed: ${response.status}` })
    return
  }

  if (!response.body) return

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        const event = parseSSELine(line.trim())
        if (event) onEvent(event)
      }
    }
  } catch (e) {
    if (!signal?.aborted) throw e
  }
}

export function generateSpec(onEvent: (event: SSEEvent) => void): void {
  consumeSSE('/api/spec/generate', onEvent, {})
}

export async function loadSpecFile(): Promise<{ spec_markdown: string; spec_version: number }> {
  const res = await fetch('/api/spec/load-file', {
    method: 'POST',
    headers: apiHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? 'Failed to load spec file')
  }
  return res.json()
}

export async function importSpec(specMarkdown: string): Promise<{ spec_version: number; length: number }> {
  const res = await fetch('/api/spec/import', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ spec_markdown: specMarkdown }),
  })
  if (!res.ok) throw new Error(`Import failed: ${res.status}`)
  return res.json()
}

export function sendChat(message: string, onEvent: (event: SSEEvent) => void): void {
  consumeSSE('/api/chat', onEvent, { message })
}

export async function validate(): Promise<ValidationResult> {
  const res = await fetch('/api/validate', { method: 'POST', headers: apiHeaders() })
  return res.json()
}

export function exportSpec(): void {
  const sessionId = getSessionId()
  const url = `/api/export?session_id=${sessionId}`
  const a = document.createElement('a')
  a.href = url
  a.download = 'spec.md'
  a.click()
}

export async function getSession(): Promise<SessionState> {
  const res = await fetch('/api/session', { headers: apiHeaders() })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export async function restoreSession(state: object): Promise<void> {
  await fetch('/api/session/restore', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(state),
  })
}

// --- Code Generation API ---

export function generateCode(onEvent: (event: SSEEvent) => void, signal?: AbortSignal): void {
  consumeSSE('/api/codegen/generate', onEvent, {}, signal)
}

export function deployAndRun(onEvent: (event: SSEEvent) => void): void {
  consumeSSE('/api/codegen/deploy', onEvent, {})
}

export async function stopContainers(): Promise<void> {
  await fetch('/api/codegen/stop', { method: 'POST', headers: apiHeaders() })
}

export async function deleteSource(): Promise<{ deleted: number; not_found: string[]; failed: string[] }> {
  const res = await fetch('/api/codegen/delete-source', { method: 'POST', headers: apiHeaders() })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
  return res.json()
}

export function downloadCode(): void {
  const sessionId = getSessionId()
  const a = document.createElement('a')
  a.href = `/api/codegen/download?session_id=${sessionId}`
  a.download = 'code.zip'
  fetch('/api/codegen/download', { headers: apiHeaders() })
    .then(res => res.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob)
      a.href = url
      a.click()
      URL.revokeObjectURL(url)
    })
}

export async function getGeneratedFiles(layer?: string): Promise<{ files: import('../types').GeneratedFile[] }> {
  const url = layer ? `/api/codegen/files?layer=${layer}` : '/api/codegen/files'
  const res = await fetch(url, { headers: apiHeaders() })
  return res.json()
}

// --- Mockup Pipeline API (원본 pfy-front 4단계 플로우) ---

export async function mockupBrief(
  projectId: string,
  projectName: string,
  briefMd: string,
): Promise<import('../types').BriefResponse> {
  const res = await fetch('/api/mockup/brief', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      project_name: projectName,
      brief_md: briefMd,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export function mockupGenerateMockup(
  onEvent: (event: import('../types').SSEEvent) => void,
): void {
  consumeSSE('/api/mockup/generate-mockup', onEvent, {})
}

export async function mockupParseInterview(
  rawInterviewText: string,
): Promise<import('../types').ParseInterviewResponse> {
  const res = await fetch('/api/mockup/parse-interview', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_interview_text: rawInterviewText }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export function mockupGenerateSpec(
  onEvent: (event: import('../types').SSEEvent) => void,
): void {
  consumeSSE('/api/mockup/generate-spec', onEvent, {})
}

export async function mockupReset(): Promise<void> {
  await fetch('/api/mockup/reset', { method: 'POST', headers: apiHeaders() })
}
