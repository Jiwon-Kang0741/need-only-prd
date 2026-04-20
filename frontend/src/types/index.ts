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
}

// --- Mockup Pipeline Types (원본 pfy-front 4단계 플로우) ---

/** project_id는 영문 대문자, 숫자, 언더스코어만 허용 */
export const PROJECT_ID_INVALID_CHARS = /[^A-Z0-9_]/g

export interface MockupState {
  projectId: string
  projectName: string
  briefMd: string | null
  mockupVue: string | null
  rawInterviewText: string | null
  interviewNotesMd: string | null
  currentStep: number
}

export interface BriefRequest {
  project_id: string
  project_name: string
  brief_md: string
}

export interface BriefResponse {
  project_id: string
  project_name: string
  current_step: number
}

export interface ParseInterviewResponse {
  interview_notes_md: string
  current_step: number
}
