import { create } from 'zustand'
import type { ChatMessage, CodeGenState, ValidationResult } from '../types'
import {
  generateSpec as apiGenerateSpec,
  sendChat as apiSendChat,
  validate as apiValidate,
  generateCode as apiGenerateCode,
  deployAndRun as apiDeployAndRun,
  stopContainers as apiStopContainers,
} from '../api/client'

const initialCodeGen: CodeGenState = {
  status: 'idle',
  plan: null,
  generatedFiles: [],
  currentFileIndex: 0,
  currentFileContent: '',
  buildLogs: [],
  error: null,
  ports: null,
}

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
  codeGen: CodeGenState
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
  generateCode: () => void
  deployAndRun: () => void
  stopContainers: () => Promise<void>
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  rawInput: null,
  specMarkdown: null,
  specVersion: 0,
  chatMessages: [],
  validationResult: null,
  isGenerating: false,
  isValidating: false,
  statusMessage: null,
  showCompare: false,
  codeGen: { ...initialCodeGen },
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
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? event.message ?? null })
      } else if ((event.type === 'chunk' || event.type === 'text') && event.content) {
        set((state) => ({ specMarkdown: (state.specMarkdown ?? '') + event.content }))
      } else if (event.type === 'complete') {
        set((state) => ({
          isGenerating: false,
          statusMessage: null,
          specVersion: event.spec_version ?? state.specVersion + 1,
        }))
      } else if (event.type === 'error') {
        set({ isGenerating: false, statusMessage: event.content ?? event.message ?? 'An error occurred' })
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
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? event.message ?? null })
      } else if ((event.type === 'chunk' || event.type === 'text') && event.content) {
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
          content: event.content ?? event.message ?? 'An error occurred.',
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

  // --- Code Generation Actions (Multi-Agent) ---
  generateCode: () => {
    set({
      codeGen: { ...initialCodeGen, status: 'generating' },
      statusMessage: 'Starting multi-agent code generation...',
    })
    apiGenerateCode((event) => {
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? event.message ?? null })
      } else if (event.type === 'agent_start') {
        // Agent started
        set({ statusMessage: `${event.display_name ?? event.agent} working...` })
      } else if (event.type === 'agent_complete') {
        // Agent completed
      } else if (event.type === 'plan' && event.plan) {
        set((state) => ({
          codeGen: { ...state.codeGen, plan: event.plan! },
        }))
      } else if (event.type === 'file_start') {
        set((state) => ({
          codeGen: {
            ...state.codeGen,
            currentFileIndex: event.index ?? state.codeGen.currentFileIndex,
            currentFileContent: '',
          },
        }))
      } else if (event.type === 'chunk' && event.content) {
        set((state) => ({
          codeGen: {
            ...state.codeGen,
            currentFileContent: state.codeGen.currentFileContent + event.content,
          },
        }))
      } else if (event.type === 'file_complete') {
        set((state) => {
          const newFile = {
            file_path: event.file_path ?? '',
            file_type: event.file_type ?? '',
            content: event.content ?? state.codeGen.currentFileContent,
            layer: (event.layer ?? 'backend') as 'backend' | 'frontend',
          }
          return {
            codeGen: {
              ...state.codeGen,
              generatedFiles: [...state.codeGen.generatedFiles, newFile],
              currentFileContent: event.content ?? '',
            },
          }
        })
      } else if (event.type === 'log' && event.line) {
        set((state) => ({
          codeGen: { ...state.codeGen, buildLogs: [...state.codeGen.buildLogs, event.line!] },
        }))
      } else if (event.type === 'complete') {
        set((state) => ({
          codeGen: { ...state.codeGen, status: 'generated' },
          statusMessage: null,
        }))
      } else if (event.type === 'error') {
        set((state) => ({
          codeGen: { ...state.codeGen, status: 'error', error: event.content ?? event.message ?? 'Generation failed' },
          statusMessage: null,
        }))
      }
    })
  },

  deployAndRun: () => {
    set((state) => ({
      codeGen: { ...state.codeGen, status: 'building', buildLogs: [], error: null, ports: null },
      statusMessage: 'Deploying to CPMS skeleton...',
    }))
    apiDeployAndRun((event) => {
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? event.message ?? null })
      } else if (event.type === 'log' && event.line) {
        set((state) => ({
          codeGen: { ...state.codeGen, buildLogs: [...state.codeGen.buildLogs, event.line!] },
        }))
      } else if (event.type === 'complete') {
        const ports = event.ports ?? null
        set((state) => ({
          codeGen: { ...state.codeGen, status: 'running', ports },
          statusMessage: null,
        }))
      } else if (event.type === 'error') {
        set((state) => ({
          codeGen: { ...state.codeGen, status: 'error', error: event.content ?? event.message ?? 'Deploy failed' },
          statusMessage: null,
        }))
      }
    })
  },

  stopContainers: async () => {
    try {
      await apiStopContainers()
      set((state) => ({
        codeGen: { ...state.codeGen, status: 'generated', ports: null },
      }))
    } catch { /* ignore */ }
  },

  reset: () => {
    const cg = get().codeGen
    if (cg.status === 'running') {
      apiStopContainers().catch(() => {})
    }
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
      codeGen: { ...initialCodeGen },
    })
  },
}))
