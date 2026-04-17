import { create } from 'zustand'
import type { ChatMessage, CodeGenState, ValidationResult, MockupState } from '../types'
import { SCREEN_ID_INVALID_CHARS } from '../types'
import {
  generateSpec as apiGenerateSpec,
  sendChat as apiSendChat,
  validate as apiValidate,
  generateCode as apiGenerateCode,
  deployAndRun as apiDeployAndRun,
  stopContainers as apiStopContainers,
  deleteSource as apiDeleteSource,
  importSpec as apiImportSpec,
  mockupAiGenerate as apiMockupAiGenerate,
  mockupScaffold as apiMockupScaffold,
  mockupAiAnnotate as apiMockupAiAnnotate,
  mockupAiInterview as apiMockupAiInterview,
  mockupInterviewResult as apiMockupInterviewResult,
  mockupGenerateSpec as apiMockupGenerateSpec,
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
  _codegenAbort: AbortController | null
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
  stopGeneration: () => void
  deployAndRun: () => void
  stopContainers: () => Promise<void>
  deleteSource: () => Promise<void>
  loadSpecFromText: (text: string) => Promise<void>

  // --- Mockup Pipeline ---
  specMode: 'text' | 'mockup'
  mockupState: MockupState | null
  mockupLoading: boolean
  mockupError: string | null
  setSpecMode: (mode: 'text' | 'mockup') => void
  mockupAiGenerate: (title: string, pageType: string, description?: string) => Promise<void>
  mockupScaffold: (screenId: string, screenName: string, pageType: string, fields: Record<string, unknown>[]) => Promise<void>
  mockupAiAnnotate: () => Promise<void>
  mockupAiInterview: () => Promise<void>
  mockupSubmitInterviewResult: (answers?: { no: number; answer: string }[], rawText?: string) => Promise<void>
  mockupGenerateSpec: () => void
  mockupGoToStep: (step: number) => void
  resetMockup: () => void
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
  _codegenAbort: null,
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
    get()._codegenAbort?.abort()
    const abort = new AbortController()
    set({
      codeGen: { ...initialCodeGen, status: 'generating' },
      statusMessage: 'Starting multi-agent code generation...',
      _codegenAbort: abort,
    })
    apiGenerateCode((event) => {
      if (abort.signal.aborted) return
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? event.message ?? null })
      } else if (event.type === 'agent_start') {
        set({ statusMessage: `${event.display_name ?? event.agent} working...` })
      } else if (event.type === 'agent_complete') {
        // no-op
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
          const existingIndex = state.codeGen.generatedFiles.findIndex(
            (f) => f.file_path === newFile.file_path
          )
          const updatedFiles =
            existingIndex >= 0
              ? state.codeGen.generatedFiles.map((f, i) => (i === existingIndex ? newFile : f))
              : [...state.codeGen.generatedFiles, newFile]
          return {
            codeGen: {
              ...state.codeGen,
              generatedFiles: updatedFiles,
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
          _codegenAbort: null,
        }))
      } else if (event.type === 'error') {
        set((state) => ({
          codeGen: { ...state.codeGen, status: 'error', error: event.content ?? event.message ?? 'Generation failed' },
          statusMessage: null,
          _codegenAbort: null,
        }))
      }
    }, abort.signal)
  },

  stopGeneration: () => {
    const abort = get()._codegenAbort
    abort?.abort()
    const hasFiles = get().codeGen.generatedFiles.length > 0
    set((state) => ({
      codeGen: {
        ...state.codeGen,
        status: hasFiles ? 'generated' : 'idle',
      },
      statusMessage: null,
      _codegenAbort: null,
    }))
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

  deleteSource: async () => {
    try {
      if (get().codeGen.status === 'running') {
        await apiStopContainers()
      }
      const result = await apiDeleteSource()
      const total = result.deleted + result.not_found.length + result.failed.length
      if (total === 0) {
        alert('삭제할 파일이 없습니다. (세션에 생성된 파일 정보가 없습니다)')
      } else if (result.failed.length > 0) {
        alert(`파일 삭제 완료: ${result.deleted}개 삭제, ${result.not_found.length}개 없음, ${result.failed.length}개 실패\n실패: ${result.failed.join('\n')}`)
      } else if (result.deleted === 0 && result.not_found.length > 0) {
        alert(`파일이 이미 삭제되었거나 경로를 찾을 수 없습니다.\n대상 경로: ${result.not_found.slice(0, 3).join('\n')}${result.not_found.length > 3 ? '\n...' : ''}`)
      }
      set({ codeGen: { ...initialCodeGen } })
    } catch (e) {
      alert(`Delete Source 실패: ${e instanceof Error ? e.message : String(e)}`)
    }
  },

  loadSpecFromText: async (text: string) => {
    const result = await apiImportSpec(text)
    set({ specMarkdown: text.trim(), specVersion: result.spec_version })
  },

  // --- Mockup Pipeline State ---
  specMode: 'text',
  mockupState: null,
  mockupLoading: false,
  mockupError: null,

  setSpecMode: (mode) => set({ specMode: mode }),

  mockupAiGenerate: async (title, pageType, description) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupAiGenerate(title, pageType, description)
      set({
        mockupState: {
          screenId: title.replace(SCREEN_ID_INVALID_CHARS, '').slice(0, 10).toUpperCase() || 'SCR001',
          screenName: title,
          pageType,
          fields: (result.fields as Record<string, unknown>[] | undefined) ?? [...(result.searchFields || []), ...(result.tableColumns || []), ...(result.formFields || [])],
          vueCode: null, annotations: null, annotationMarkdown: null,
          interviewQuestions: null, interviewAnswers: null, rawInterviewText: null, interviewNoteMd: null,
          currentStep: 1,
        },
        mockupLoading: false,
      })
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupScaffold: async (screenId, screenName, pageType, fields) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupScaffold(screenId, screenName, pageType, fields)
      set((state) => ({
        mockupState: state.mockupState ? { ...state.mockupState, screenId, screenName, pageType, fields, vueCode: result.vue_code, currentStep: 2 } : null,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupAiAnnotate: async () => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupAiAnnotate()
      set((state) => ({
        mockupState: state.mockupState ? { ...state.mockupState, annotationMarkdown: result.annotation_markdown, currentStep: 3 } : null,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupAiInterview: async () => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupAiInterview()
      set((state) => ({
        mockupState: state.mockupState ? { ...state.mockupState, interviewQuestions: result.questions, currentStep: 4 } : null,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupSubmitInterviewResult: async (answers, rawText) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupInterviewResult(answers, rawText)
      set((state) => ({
        mockupState: state.mockupState ? { ...state.mockupState, interviewAnswers: answers || null, rawInterviewText: rawText || null, interviewNoteMd: result.interview_note_md, currentStep: 5 } : null,
        specVersion: result.spec_version,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupGenerateSpec: () => {
    set({ isGenerating: true, statusMessage: 'Generating spec from interview results...', specMarkdown: null })
    apiMockupGenerateSpec((event) => {
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? event.message ?? null })
      } else if ((event.type === 'chunk' || event.type === 'text') && event.content) {
        set((state) => ({ specMarkdown: (state.specMarkdown ?? '') + event.content }))
      } else if (event.type === 'complete') {
        set((state) => ({
          isGenerating: false, statusMessage: null,
          specVersion: event.spec_version ?? state.specVersion + 1,
          mockupState: state.mockupState ? { ...state.mockupState, currentStep: 6 } : null,
        }))
      } else if (event.type === 'error') {
        set({ isGenerating: false, statusMessage: event.content ?? event.message ?? 'An error occurred' })
      }
    })
  },

  mockupGoToStep: (step) => set((state) => ({
    mockupState: state.mockupState ? { ...state.mockupState, currentStep: step } : null,
  })),

  resetMockup: () => set({ mockupState: null, mockupLoading: false, mockupError: null }),

  reset: () => {
    get()._codegenAbort?.abort()
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
      _codegenAbort: null,
      specMode: 'text',
      mockupState: null,
      mockupLoading: false,
      mockupError: null,
    })
  },
}))
