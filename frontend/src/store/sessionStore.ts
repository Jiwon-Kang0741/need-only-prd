import { create } from 'zustand'
import type { ChatMessage, ValidationResult } from '../types'
import { generateSpec as apiGenerateSpec, sendChat as apiSendChat, validate as apiValidate } from '../api/client'

interface SessionStore {
  rawInput: string | null
  specMarkdown: string | null
  specVersion: number
  chatMessages: ChatMessage[]
  validationResult: ValidationResult | null
  isGenerating: boolean
  isValidating: boolean
  statusMessage: string | null
  showCompare: boolean
  setRawInput: (input: string | null) => void
  appendSpecChunk: (chunk: string) => void
  setSpecMarkdown: (markdown: string | null) => void
  setSpecVersion: (version: number) => void
  addChatMessage: (message: ChatMessage) => void
  setValidation: (result: ValidationResult | null) => void
  setGenerating: (generating: boolean) => void
  setStatus: (message: string | null) => void
  generateSpec: () => void
  sendChatMessage: (message: string) => void
  validateCoverage: () => Promise<void>
  toggleCompare: () => void
  reset: () => void
}

export const useSessionStore = create<SessionStore>((set) => ({
  rawInput: null,
  specMarkdown: null,
  specVersion: 0,
  chatMessages: [],
  validationResult: null,
  isGenerating: false,
  isValidating: false,
  statusMessage: null,
  showCompare: false,
  setRawInput: (input) => set({ rawInput: input }),
  appendSpecChunk: (chunk) => set((state) => ({ specMarkdown: (state.specMarkdown ?? '') + chunk })),
  setSpecMarkdown: (markdown) => set({ specMarkdown: markdown }),
  setSpecVersion: (version) => set({ specVersion: version }),
  addChatMessage: (message) => set((state) => ({ chatMessages: [...state.chatMessages, message] })),
  setValidation: (result) => set({ validationResult: result }),
  setGenerating: (generating) => set({ isGenerating: generating }),
  setStatus: (message) => set({ statusMessage: message }),
  generateSpec: () => {
    set({ isGenerating: true, statusMessage: 'Analyzing requirements...', specMarkdown: null })
    apiGenerateSpec((event) => {
      if (event.type === 'status' && event.message) {
        set({ statusMessage: event.message })
      } else if (event.type === 'text' && event.content) {
        set((state) => ({ specMarkdown: (state.specMarkdown ?? '') + event.content }))
      } else if (event.type === 'complete') {
        set((state) => ({
          isGenerating: false,
          statusMessage: null,
          specVersion: event.spec_version ?? state.specVersion + 1,
        }))
      } else if (event.type === 'error') {
        set({ isGenerating: false, statusMessage: event.message ?? 'An error occurred' })
      }
    })
  },
  sendChatMessage: (message: string) => {
    const userMsg: ChatMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    }
    set((state) => ({
      chatMessages: [...state.chatMessages, userMsg],
      isGenerating: true,
      statusMessage: 'Updating spec...',
    }))

    let assistantContent = ''

    apiSendChat(message, (event) => {
      if (event.type === 'status' && event.message) {
        set({ statusMessage: event.message })
      } else if (event.type === 'text' && event.content) {
        assistantContent += event.content
        set((state) => ({ specMarkdown: (state.specMarkdown ?? '') + event.content }))
      } else if (event.type === 'complete') {
        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: assistantContent || 'Spec updated.',
          timestamp: new Date().toISOString(),
        }
        set((state) => ({
          isGenerating: false,
          statusMessage: null,
          specVersion: event.spec_version ?? state.specVersion + 1,
          chatMessages: [...state.chatMessages, assistantMsg],
        }))
      } else if (event.type === 'error') {
        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: event.message ?? 'An error occurred.',
          timestamp: new Date().toISOString(),
        }
        set((state) => ({
          isGenerating: false,
          statusMessage: null,
          chatMessages: [...state.chatMessages, assistantMsg],
        }))
      }
    })
  },
  validateCoverage: async () => {
    set({ isValidating: true })
    try {
      const result = await apiValidate()
      set({ validationResult: result, isValidating: false })
    } catch {
      set({ isValidating: false })
    }
  },
  toggleCompare: () => set((state) => ({ showCompare: !state.showCompare })),
  reset: () => {
    // Clear session storage so a new session ID is generated
    sessionStorage.removeItem('session_id')
    set({
      rawInput: null,
      specMarkdown: null,
      specVersion: 0,
      chatMessages: [],
      validationResult: null,
      isGenerating: false,
      isValidating: false,
      statusMessage: null,
      showCompare: false,
    })
  },
}))
