import { useEffect, useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'
import { PROJECT_ID_INVALID_CHARS } from '../../types'

const DEFAULT_BRIEF_TEMPLATE = `# 프로젝트 개요
- 프로젝트명:
- 목적:
- 대상 사용자:

# 사용자 역할
- ADMIN:
- USER:

# 핵심 기능
1.
2.
3.

# 예상 화면 목록
- 화면1
- 화면2

# 기술 제약
- Spring Boot 3.x, Java 21, JPA, Querydsl
`

export default function Step1Brief() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const setBrief = useSessionStore((s) => s.mockupSetBrief)

  const [projectId, setProjectId] = useState(mockupState?.projectId ?? '')
  const [projectName, setProjectName] = useState(mockupState?.projectName ?? '')
  const [briefMd, setBriefMd] = useState(mockupState?.briefMd ?? DEFAULT_BRIEF_TEMPLATE)

  useEffect(() => {
    if (mockupState) {
      setProjectId(mockupState.projectId)
      setProjectName(mockupState.projectName)
      setBriefMd(mockupState.briefMd ?? DEFAULT_BRIEF_TEMPLATE)
    }
  }, [mockupState])

  const canSubmit =
    projectId.trim().length > 0 &&
    projectName.trim().length > 0 &&
    briefMd.trim().length > 0 &&
    !loading

  async function handleSubmit() {
    if (!canSubmit) return
    await setBrief(projectId, projectName, briefMd)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold font-headline text-on-surface mb-1">① Brief 작성</h2>
        <p className="text-sm text-on-surface-variant">
          프로젝트 전체 정보를 5분 안에 채워주세요. 이 정보를 바탕으로 Mockup이 생성됩니다.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-bold text-on-surface mb-1 block">Project ID *</label>
          <input
            type="text"
            value={projectId}
            onChange={(e) =>
              setProjectId(e.target.value.toUpperCase().replace(PROJECT_ID_INVALID_CHARS, ''))
            }
            placeholder="예: ETHICS_REPORT"
            className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={loading}
          />
          <p className="text-xs text-on-surface-variant mt-1">영문 대문자, 숫자, 언더스코어만 허용</p>
        </div>
        <div>
          <label className="text-sm font-bold text-on-surface mb-1 block">프로젝트명 *</label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="예: 윤리경영시스템"
            className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={loading}
          />
        </div>
      </div>

      <div>
        <label className="text-sm font-bold text-on-surface mb-1 block">brief.md *</label>
        <textarea
          value={briefMd}
          onChange={(e) => setBriefMd(e.target.value)}
          rows={20}
          className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={loading}
        />
      </div>

      {error && (
        <div className="bg-error-container text-on-error-container px-4 py-2 rounded-lg text-sm">{error}</div>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? '저장 중...' : '다음: Mockup 생성 →'}
        </button>
      </div>
    </div>
  )
}
