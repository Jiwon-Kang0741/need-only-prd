import { create } from 'zustand'
import type { ChatMessage, CodeGenState, ValidationResult, MockupState } from '../types'
import {
  generateSpec as apiGenerateSpec,
  sendChat as apiSendChat,
  validate as apiValidate,
  generateCode as apiGenerateCode,
  deployAndRun as apiDeployAndRun,
  stopContainers as apiStopContainers,
  deleteSource as apiDeleteSource,
  importSpec as apiImportSpec,
  mockupBrief as apiMockupBrief,
  mockupGenerateMockup as apiMockupGenerateMockup,
  mockupParseInterview as apiMockupParseInterview,
  mockupGenerateSpec as apiMockupGenerateSpec,
  mockupReset as apiMockupReset,
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

  // --- Mockup Pipeline (원본 pfy-front 4단계) ---
  specMode: 'text' | 'mockup'
  mockupState: MockupState | null
  mockupLoading: boolean
  mockupError: string | null
  setSpecMode: (mode: 'text' | 'mockup') => void
  mockupSetBrief: (projectId: string, projectName: string, briefMd: string) => Promise<void>
  mockupGenerateMockup: () => void
  mockupParseInterview: (rawText: string) => Promise<void>
  mockupGenerateSpec: () => void
  mockupGoToStep: (step: number) => void
  resetMockup: () => Promise<void>
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

  specMode: 'text',
  mockupState: null,
  mockupLoading: false,
  mockupError: null,

  setSpecMode: (mode) => set({ specMode: mode }),

  mockupSetBrief: async (projectId, projectName, briefMd) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      await apiMockupBrief(projectId, projectName, briefMd)
      set({
        mockupState: {
          projectId, projectName, briefMd,
          mockupVue: null, rawInterviewText: null, interviewNotesMd: null,
          currentStep: 2,   // Step2로 바로 이동 (Brief 완료)
        },
        mockupLoading: false,
      })
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupGenerateMockup: () => {
    set({ mockupLoading: true, mockupError: null, statusMessage: 'Generating Mockup.vue...' })
    let acc = ''
    apiMockupGenerateMockup((event) => {
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? null })
      } else if ((event.type === 'chunk' || event.type === 'text') && event.content) {
        acc += event.content
        set((state) => ({
          mockupState: state.mockupState
            ? { ...state.mockupState, mockupVue: acc }
            : null,
        }))
      } else if (event.type === 'complete') {
        set((state) => ({
          mockupState: state.mockupState ? { ...state.mockupState, currentStep: 3 } : null,
          mockupLoading: false,
          statusMessage: null,
        }))
      } else if (event.type === 'error') {
        set({
          mockupError: event.content ?? event.message ?? 'Mockup 생성 실패',
          mockupLoading: false,
          statusMessage: null,
        })
      }
    })
  },

  mockupParseInterview: async (rawText) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupParseInterview(rawText)
      set((state) => ({
        mockupState: state.mockupState
          ? {
              ...state.mockupState,
              rawInterviewText: rawText,
              interviewNotesMd: result.interview_notes_md,
              currentStep: 4,
            }
          : null,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupGenerateSpec: () => {
    set({
      isGenerating: true,
      statusMessage: 'Generating spec.md...',
      specMarkdown: null,
    })
    apiMockupGenerateSpec((event) => {
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? null })
      } else if ((event.type === 'chunk' || event.type === 'text') && event.content) {
        set((state) => ({ specMarkdown: (state.specMarkdown ?? '') + event.content }))
      } else if (event.type === 'complete') {
        set((state) => ({
          isGenerating: false,
          statusMessage: null,
          specVersion: event.spec_version ?? state.specVersion + 1,
        }))
      } else if (event.type === 'error') {
        set({
          isGenerating: false,
          statusMessage: event.content ?? 'Spec 생성 실패',
        })
      }
    })
  },

  mockupGoToStep: (step) =>
    set((state) => ({
      mockupState: state.mockupState
        ? { ...state.mockupState, currentStep: step }
        : null,
    })),

  resetMockup: async () => {
    try {
      await apiMockupReset()
    } catch { /* ignore */ }
    set({ mockupState: null, mockupLoading: false, mockupError: null })
  },

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
