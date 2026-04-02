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
  type: 'status' | 'text' | 'requirements' | 'complete' | 'error'
  content?: string
  spec_version?: number
  message?: string
}
