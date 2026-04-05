import type { SessionState, SSEEvent, ValidationResult } from '../types'

function getSessionId(): string {
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

async function consumeSSE(url: string, onEvent: (event: SSEEvent) => void, body?: object): Promise<void> {
  const response = await fetch(url, {
    method: body ? 'POST' : 'GET',
    headers: { ...apiHeaders(), ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })

  if (!response.body) return

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

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
}

export function generateSpec(onEvent: (event: SSEEvent) => void): void {
  consumeSSE('/api/spec/generate', onEvent, {})
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

export function generateCode(onEvent: (event: SSEEvent) => void): void {
  consumeSSE('/api/codegen/generate', onEvent, {})
}

export function deployAndRun(onEvent: (event: SSEEvent) => void): void {
  consumeSSE('/api/codegen/deploy', onEvent, {})
}

export async function stopContainers(): Promise<void> {
  await fetch('/api/codegen/stop', { method: 'POST', headers: apiHeaders() })
}

export function downloadCode(): void {
  const sessionId = getSessionId()
  const a = document.createElement('a')
  a.href = `/api/codegen/download?session_id=${sessionId}`
  a.download = 'code.zip'
  // Need to add session header via fetch for download
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
