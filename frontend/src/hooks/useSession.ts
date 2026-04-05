import { useEffect } from 'react'
import { getSession, restoreSession } from '../api/client'
import { useSessionStore } from '../store/sessionStore'
import type { CodeGenState } from '../types'

const CACHE_KEY = 'session_state_cache'

export function useSession() {
  const store = useSessionStore()

  useEffect(() => {
    async function init() {
      try {
        const state = await getSession()
        if (state.raw_input) store.setRawInput(state.raw_input.text)
        if (state.spec_markdown) store.setSpecMarkdown(state.spec_markdown)
        if (state.chat_history) state.chat_history.forEach(store.addChatMessage)
        if (state.validation_result) store.setValidation(state.validation_result)

        // Restore codegen state if available
        const cg = (state as unknown as Record<string, unknown>).codegen as Record<string, unknown> | null
        if (cg && cg.status && cg.status !== 'idle') {
          const restored: CodeGenState = {
            status: (cg.status as CodeGenState['status']) ?? 'idle',
            plan: (cg.plan as CodeGenState['plan']) ?? null,
            generatedFiles: (cg.generated_files as CodeGenState['generatedFiles']) ?? [],
            currentFileIndex: 0,
            currentFileContent: '',
            buildLogs: [],
            error: (cg.error as string) ?? null,
            ports: null,
          }
          useSessionStore.setState({ codeGen: restored })
        }

        sessionStorage.setItem(CACHE_KEY, JSON.stringify(state))
      } catch (err: unknown) {
        if (err instanceof Error && err.message === '404') {
          const cached = sessionStorage.getItem(CACHE_KEY)
          if (cached) {
            try {
              await restoreSession(JSON.parse(cached))
            } catch {
              store.reset()
            }
          }
        }
      }
    }
    init()
  }, [])
}
