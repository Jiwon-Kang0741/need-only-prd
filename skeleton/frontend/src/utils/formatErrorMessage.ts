export function formatErrorMessage(error: unknown, fallback?: string): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  if (error && typeof error === 'object') {
    const e = error as Record<string, unknown>
    if (e.data && typeof e.data === 'object') {
      const data = e.data as Record<string, unknown>
      if (data.header && typeof data.header === 'object') {
        return (data.header as Record<string, unknown>).responseMessage as string || fallback || 'Unknown error'
      }
    }
  }
  return fallback || 'Unknown error'
}

export default formatErrorMessage
