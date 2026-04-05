import { useSessionStore } from '../store/sessionStore'

export default function CoverageScore() {
  const validationResult = useSessionStore((s) => s.validationResult)
  const isValidating = useSessionStore((s) => s.isValidating)
  const validateCoverage = useSessionStore((s) => s.validateCoverage)
  const specMarkdown = useSessionStore((s) => s.specMarkdown)

  const score = validationResult?.score ?? null

  return (
    <div className="flex flex-col gap-2">
      {score === null || !validationResult ? (
        <button
          onClick={validateCoverage}
          disabled={isValidating || !specMarkdown}
          className="bg-tertiary text-on-tertiary px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="material-symbols-outlined text-[18px]">verified</span>
          {isValidating ? 'Validating...' : 'Validate Coverage'}
        </button>
      ) : (
        <>
          <div className="flex-1 min-w-[240px] bg-tertiary-fixed/30 p-3 rounded-xl border border-tertiary-fixed/50 flex items-center gap-4">
            {/* Circular progress */}
            <div className="relative w-10 h-10 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 40 40">
                <circle
                  className="text-on-tertiary-container/10"
                  cx="20"
                  cy="20"
                  r="16"
                  fill="transparent"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <circle
                  className="text-tertiary"
                  cx="20"
                  cy="20"
                  r="16"
                  fill="transparent"
                  stroke="currentColor"
                  strokeWidth="4"
                  strokeDasharray="100"
                  strokeDashoffset={100 - score}
                />
              </svg>
              <span className="absolute text-[10px] font-bold text-tertiary">
                {score}%
              </span>
            </div>

            {/* Score details */}
            <div className="flex-1">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] font-bold text-tertiary uppercase tracking-widest">
                  Coverage Score
                </span>
                <span className="text-[10px] font-semibold text-secondary">
                  {validationResult.covered.length}/{validationResult.covered.length + validationResult.missing.length}
                </span>
              </div>
              <div className="h-1.5 w-full bg-on-tertiary-container/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-tertiary transition-all"
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>
          </div>

          {/* Collapsible details */}
          <div className="flex flex-col gap-1">
            {validationResult.covered.length > 0 && (
              <details className="cursor-pointer">
                <summary className="text-[10px] font-bold uppercase tracking-widest cursor-pointer select-none text-primary">
                  Covered ({validationResult.covered.length})
                </summary>
                <ul className="mt-1 space-y-0.5 pl-1">
                  {validationResult.covered.map((item) => (
                    <li key={item.id} className="flex items-start gap-1 text-xs text-on-surface-variant">
                      <span className="text-primary mt-0.5">&#10003;</span>
                      <span>{item.description ?? item.id}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}

            {validationResult.missing.length > 0 && (
              <details className="cursor-pointer">
                <summary className="text-[10px] font-bold uppercase tracking-widest cursor-pointer select-none text-error">
                  Missing ({validationResult.missing.length})
                </summary>
                <ul className="mt-1 space-y-0.5 pl-1">
                  {validationResult.missing.map((item) => (
                    <li key={item.id} className="flex items-start gap-1 text-xs text-on-surface-variant">
                      <span className="text-error mt-0.5">&#10007;</span>
                      <span>{item.reason ?? item.description ?? item.id}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}

            {validationResult.suggestions.length > 0 && (
              <details className="cursor-pointer">
                <summary className="text-[10px] font-bold uppercase tracking-widest cursor-pointer select-none text-tertiary">
                  Suggestions ({validationResult.suggestions.length})
                </summary>
                <ul className="mt-1 space-y-0.5 pl-1 list-disc list-inside text-xs text-on-surface-variant">
                  {validationResult.suggestions.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        </>
      )}
    </div>
  )
}
