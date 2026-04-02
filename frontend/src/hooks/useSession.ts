import { useEffect } from 'react'
import { getSession, restoreSession } from '../api/client'
import { useSessionStore } from '../store/sessionStore'

const CACHE_KEY = 'session_state_cache'

export function useSession() {
  const { setRawInput, setSpecMarkdown, addChatMessage, setValidation, reset } = useSessionStore()

  useEffect(() => {
    async function init() {
      try {
        const state = await getSession()
        if (state.raw_input) setRawInput(state.raw_input.text)
        if (state.spec_markdown) setSpecMarkdown(state.spec_markdown)
        if (state.chat_history) state.chat_history.forEach(addChatMessage)
        if (state.validation_result) setValidation(state.validation_result)
        sessionStorage.setItem(CACHE_KEY, JSON.stringify(state))
      } catch (err: unknown) {
        if (err instanceof Error && err.message === '404') {
          const cached = sessionStorage.getItem(CACHE_KEY)
          if (cached) {
            try {
              await restoreSession(JSON.parse(cached))
            } catch {
              reset()
            }
          }
        }
      }
    }
    init()
  }, [])
}
