export interface RawInput {
  text: string
  source_type: string
  uploaded_at: string
}

export interface ExtractedRequirements {
  requirements: Requirement[]
  source_references: string[]
  extraction_confidence: number
}

export interface Requirement {
  id: string
  description: string
  priority: 'high' | 'medium' | 'low'
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface ValidationResult {
  score: number
  covered: CoverageItem[]
  missing: CoverageItem[]
  suggestions: string[]
}

export interface CoverageItem {
  id: string
  description?: string
  evidence?: string
  reason?: string
}

export interface SessionState {
  session_id: string
  created_at: string
  raw_input: RawInput | null
  extracted_requirements: ExtractedRequirements | null
  spec_markdown: string | null
  spec_version: number
  chat_history: ChatMessage[]
  validation_result: ValidationResult | null
}

export interface SSEEvent {
  type: 'status' | 'text' | 'chunk' | 'requirements' | 'complete' | 'error'
      | 'plan' | 'file_start' | 'file_complete' | 'log'
      | 'agent_start' | 'agent_complete'
      // LangGraph agentic events
      | 'node_start' | 'node_end'
      | 'wave_start' | 'wave_complete'
      | 'contract'
      | 'tool_call' | 'tool_result'
      | 'react_step' | 'react_converged'
      | 'graph_complete'
  content?: string
  spec_version?: number
  message?: string
  // codegen fields
  plan?: CodeGenPlan
  index?: number
  total?: number
  file_path?: string
  file_type?: string
  layer?: string
  description?: string
  line?: string
  status?: Record<string, unknown>
  ports?: { db?: number; backend?: number; frontend?: number }
  agent?: string
  display_name?: string
  files_count?: number
  // LangGraph agentic fields
  node?: string
  wave?: number
  file_count?: number
  path?: string
  tool?: string
  args?: Record<string, unknown>
  contract?: Record<string, unknown>
  files?: Array<{ file_path?: string; path?: string; file_type?: string; wave?: number }>
  iteration?: number
  thought?: string
  reason?: string
}

// --- Code Generation Types ---

export interface CodeGenPlanFile {
  file_path: string
  file_type: string
  layer: 'backend' | 'frontend'
  description: string
  depends_on: string[]
}

export interface CodeGenPlan {
  files: CodeGenPlanFile[]
  module_code: string
  screen_code: string
}

export interface GeneratedFile {
  file_path: string
  file_type: string
  content: string
  layer: 'backend' | 'frontend'
}

export interface CodeGenState {
  status: 'idle' | 'planning' | 'planned' | 'generating' | 'generated' | 'building' | 'running' | 'error'
  plan: CodeGenPlan | null
  generatedFiles: GeneratedFile[]
  currentFileIndex: number
  currentFileContent: string
  buildLogs: string[]
  error: string | null
  ports: { db?: number; backend?: number; frontend?: number } | null
  // LangGraph progress
  currentNode: string | null
  currentWave: number | null
  reactSteps: Array<{ iteration?: number; tool?: string; thought?: string }>
  plannedFiles: Array<{ path: string; file_type?: string; wave?: number }>
  completedPaths: string[]
}

// --- Mockup Pipeline Types ---

/** screenId 는 영문/숫자/언더스코어만 허용 (backend _PFY_FRONT 경로 안전성 보장) */
export const SCREEN_ID_INVALID_CHARS = /[^A-Za-z0-9_]/g

export interface FieldOption {
  label: string
  value: string
  color?: string
}

export interface FieldDef {
  key: string
  label: string
  type: 'text' | 'number' | 'select' | 'radio' | 'badge' | 'date' | 'daterange' | 'textarea' | 'checkbox'
  searchable?: boolean
  listable?: boolean
  detailable?: boolean
  editable?: boolean
  required?: boolean
  options?: FieldOption[]
  width?: string
}

export interface InterviewQuestion {
  no: number
  category: string
  question: string
  priority: '높음' | '보통' | '낮음'
  tip: string
}

export interface MockupState {
  screenId: string
  screenName: string
  pageType: string
  fields: Record<string, unknown>[]
  menuContext?: {
    menu_id?: string
    menu_name?: string
    p_menu_id?: string
    parent_menu_id?: string
    component_key?: string | null
    lv2_pascal?: string | null
    sort_num?: number
    screen_id?: string
    roles?: string[]
    source?: string
  } | null
  vueCode: string | null
  annotations: Record<string, unknown>[] | null
  annotationMarkdown: string | null
  interviewQuestions: InterviewQuestion[] | null
  interviewAnswers: { no: number; answer: string }[] | null
  rawInterviewText: string | null
  interviewNoteMd: string | null
  currentStep: number
}

export interface AiGenerateResult {
  success: boolean
  /** 백엔드·LLM이 도출한 CPMS PascalCase 화면코드 */
  screen_id?: string
  screen_name?: string
  domain?: string
  menu_context?: Record<string, unknown>
  fields?: Record<string, unknown>[]
  searchFields?: Record<string, unknown>[]
  tableColumns?: Record<string, unknown>[]
  mockRows?: Record<string, unknown>[]
  formFields?: Record<string, unknown>[]
}

export interface ScaffoldResult {
  success: boolean
  vue_code: string
}

export interface AnnotateResult {
  success: boolean
  annotation_count: number
  annotation_markdown: string
}

export interface InterviewResult {
  success: boolean
  questions: InterviewQuestion[]
}

export interface InterviewResultResponse {
  success: boolean
  interview_note_md: string
  spec_version: number
}
