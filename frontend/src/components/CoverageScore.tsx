import { useSessionStore } from '../store/sessionStore'

export default function CoverageScore() {
  const validationResult = useSessionStore((s) => s.validationResult)
  const isValidating = useSessionStore((s) => s.isValidating)
  const validateCoverage = useSessionStore((s) => s.validateCoverage)
  const specMarkdown = useSessionStore((s) => s.specMarkdown)

  const score = validationResult?.score ?? null

  function scoreColor(s: number): string {
    if (s >= 80) return 'bg-green-500'
    if (s >= 50) return 'bg-yellow-400'
    return 'bg-red-500'
  }

  function scoreLabelColor(s: number): string {
    if (s >= 80) return 'text-green-700'
    if (s >= 50) return 'text-yellow-700'
    return 'text-red-700'
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={validateCoverage}
        disabled={isValidating || !specMarkdown}
        className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          isValidating || !specMarkdown
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
            : 'bg-purple-600 text-white hover:bg-purple-700'
        }`}
      >
        {isValidating ? 'Validating...' : 'Validate Coverage'}
      </button>

      {score !== null && validationResult && (
        <div className="bg-white border rounded-lg p-3 text-sm space-y-2 min-w-[220px]">
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-700">Coverage</span>
            <span className={`font-bold text-base ${scoreLabelColor(score)}`}>{score}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${scoreColor(score)}`}
              style={{ width: `${score}%` }}
            />
          </div>

          {validationResult.covered.length > 0 && (
            <details className="cursor-pointer">
              <summary className="text-green-700 font-medium select-none">
                Covered ({validationResult.covered.length})
              </summary>
              <ul className="mt-1 space-y-0.5 pl-1">
                {validationResult.covered.map((item) => (
                  <li key={item.id} className="flex items-start gap-1 text-gray-700">
                    <span className="text-green-500 mt-0.5">&#10003;</span>
                    <span>{item.description ?? item.id}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}

          {validationResult.missing.length > 0 && (
            <details className="cursor-pointer">
              <summary className="text-red-700 font-medium select-none">
                Missing ({validationResult.missing.length})
              </summary>
              <ul className="mt-1 space-y-0.5 pl-1">
                {validationResult.missing.map((item) => (
                  <li key={item.id} className="flex items-start gap-1 text-gray-700">
                    <span className="text-red-500 mt-0.5">&#10007;</span>
                    <span>{item.reason ?? item.description ?? item.id}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}

          {validationResult.suggestions.length > 0 && (
            <details className="cursor-pointer">
              <summary className="text-blue-700 font-medium select-none">
                Suggestions ({validationResult.suggestions.length})
              </summary>
              <ul className="mt-1 space-y-0.5 pl-1 list-disc list-inside text-gray-700">
                {validationResult.suggestions.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  )
}
