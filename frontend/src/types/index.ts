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
