import express, { Request, Response } from 'express';
import fs from 'fs';
import path from 'path';

import { callLLM, extractJson } from '../utils/llmClient';
import { PATHS } from '../utils/paths';

const router = express.Router();

interface InterviewRequestBody {
  pageType?: string;
  title?: string;
  description?: string;
  pageName?: string;
  routePath?: string;
  searchFields?: unknown[];
  tableColumns?: unknown[];
  formFields?: unknown[];
  actions?: string[];
  mockDataCount?: number;
  annotationMarkdown?: string; // UI 주석 자동생성 결과 (있으면 우선 사용)
  vueSource?: string;          // MockUp 소스 코드 (annotationMarkdown과 함께 사용)
}

// ─────────────────────────────────────────────────────────────────────────────
//  공통 Role / Context / Rules
// ─────────────────────────────────────────────────────────────────────────────
const INTERVIEW_ROLE_CONTEXT = `# Role
당신은 엔터프라이즈 시스템 전문 IT 비즈니스 분석가(BA)입니다.
제공된 [MockUp 코드]와 [컴포넌트 주석 테이블]을 분석하여, 설계 확정을 위한 핵심 인터뷰 질문 10개를 생성해 주세요.

# Context
이 인터뷰의 목적은 목업 단계의 가설을 확정하여 Back-End API 설계서와 DB 정의서를 포함한 Spec.md를 도출하기 위함입니다.
따라서 질문은 매우 구체적이고 기술적 의사결정을 포함해야 합니다.

# Question Generation Rules
1. 데이터 스펙 확정: 각 필드의 타입, 길이, 필수 여부를 확인하는 질문 포함.
2. 검색 및 정렬 로직: 검색 시 일치 조건(Like vs Equal)과 기본 정렬 순서 확인.
3. 비즈니스 예외 케이스: 데이터가 없거나, 권한이 없거나, 서버 오류 시의 사용자 경험 확인.
4. 연동 및 출력: 엑셀 다운로드 범위, 타 시스템 연동 데이터 등에 대한 질문.
5. 어조: 전문적이면서도 현업이 이해하기 쉬운 비즈니스 용어 사용.`;

const QUESTION_OUTPUT_FORMAT = `# Output Format
반드시 아래 JSON 형식으로만 응답하세요 (코드블록·설명 문장 없이 순수 JSON만):
{
  "questions": [
    {
      "category": "조회조건|데이터정의|사용자행동|권한|예외처리 중 하나",
      "question": "인터뷰 시 그대로 읽을 수 있는 구체적인 질문 (보충 질문 포함)",
      "priority": "높음|보통|낮음 중 하나",
      "tip": "현재 목업은 ~로 설계되어 있습니다. 이대로 진행해도 될까요? 형태의 설계 가설 (1~2문장)"
    }
  ]
}

규칙:
- questions 배열 길이는 정확히 10
- category는 조회조건 / 데이터정의 / 사용자행동 / 권한 / 예외처리 중 하나
- question은 예/아니오만으로 끝나는 질문은 반드시 보충 질문을 포함
- priority는 반드시 "높음" | "보통" | "낮음" 중 하나 (업무 영향도·구현 의존성 기준)
- tip은 목업 현황을 근거로 한 설계 가설 문장`;

// ─────────────────────────────────────────────────────────────────────────────
//  Prompt Builders
// ─────────────────────────────────────────────────────────────────────────────

/** 주석 + MockUp 소스를 1차 소스로 사용하는 프롬프트 */
function buildPromptFromAnnotation(ctx: InterviewRequestBody): string {
  const sourceSection = ctx.vueSource?.trim()
    ? `\n\n--- MockUp 소스 코드 시작 ---\n\`\`\`vue\n${ctx.vueSource}\n\`\`\`\n--- MockUp 소스 코드 끝 ---`
    : '';

  return `${INTERVIEW_ROLE_CONTEXT}

아래는 "${ctx.title}" 화면에 대해 자동 생성된 컴포넌트 주석 테이블입니다.
이 주석에 명시된 기능·로직·업무 규칙·예외 처리 내용을 검토하여, 아직 정의되지 않았거나 모호해 보이는 지점을 찾아 고객/현업에게 물어볼 인터뷰 질문을 정확히 10개 작성해 주세요.

--- 컴포넌트 주석 테이블 시작 ---
${ctx.annotationMarkdown}
--- 컴포넌트 주석 테이블 끝 ---${sourceSection}

${QUESTION_OUTPUT_FORMAT}`;
}

/** 화면 스펙 JSON을 소스로 사용하는 프롬프트 (주석 없을 때 fallback) */
function buildPromptFromSpec(ctx: InterviewRequestBody): string {
  const specJson = JSON.stringify(
    {
      pageType:      ctx.pageType,
      title:         ctx.title,
      description:   ctx.description,
      pageName:      ctx.pageName,
      routePath:     ctx.routePath,
      searchFields:  ctx.searchFields ?? [],
      tableColumns:  ctx.tableColumns ?? [],
      formFields:    ctx.formFields ?? [],
      actions:       ctx.actions ?? [],
      mockDataCount: ctx.mockDataCount,
    },
    null,
    2,
  );

  const sourceSection = ctx.vueSource?.trim()
    ? `\n\n--- MockUp 소스 코드 시작 ---\n\`\`\`vue\n${ctx.vueSource}\n\`\`\`\n--- MockUp 소스 코드 끝 ---`
    : '';

  return `${INTERVIEW_ROLE_CONTEXT}

아래는 MockUp Builder에서 정의된 "${ctx.title}" 화면 스펙(JSON)입니다.
이 화면만 보고 아직 정의되지 않았거나 모호해 보이는 지점을 찾아, 고객/현업에게 물어볼 인터뷰 질문을 정확히 10개 작성해 주세요.

--- 화면 스펙 시작 ---
${specJson}
--- 화면 스펙 끝 ---${sourceSection}

${QUESTION_OUTPUT_FORMAT}`;
}

function buildInterviewPrompt(ctx: InterviewRequestBody): { prompt: string; source: 'annotation' | 'spec' } {
  if (ctx.annotationMarkdown?.trim()) {
    return { prompt: buildPromptFromAnnotation(ctx), source: 'annotation' };
  }
  return { prompt: buildPromptFromSpec(ctx), source: 'spec' };
}

// ─────────────────────────────────────────────────────────────────────────────
//  POST /api/ai-interview-questions
// ─────────────────────────────────────────────────────────────────────────────
router.post('/', async (req: Request, res: Response) => {
  const body = req.body as InterviewRequestBody;

  if (!body.title?.trim()) {
    return res.status(400).json({ success: false, message: '화면 제목(title)은 필수입니다.' });
  }

  // pageName 이 있고 vueSource 가 없으면 생성된 .vue 파일을 자동으로 읽어 주입
  if (!body.vueSource?.trim() && body.pageName?.trim()) {
    const safeName = body.pageName.trim();
    if (/^[A-Za-z0-9_-]+$/.test(safeName)) {
      const filePath = path.join(PATHS.pagesGenerated, `${safeName}.vue`);
      if (fs.existsSync(filePath)) {
        body.vueSource = fs.readFileSync(filePath, 'utf-8');
      }
    }
  }

  const { prompt, source } = buildInterviewPrompt(body);
  console.log(`[ai-interview] "${body.title}" (${body.pageType ?? '?'}) source=${source} vueSource=${body.vueSource ? body.vueSource.length + 'chars' : 'none'}`);

  try {
    const raw = await callLLM(
      [
        {
          role: 'system',
          content:
            '당신은 엔터프라이즈 시스템 전문 IT 비즈니스 분석가(BA)입니다. 지정한 JSON 스키마로만 답하고, questions는 반드시 10개입니다.',
        },
        { role: 'user', content: prompt },
      ],
      3200,
    );

    const parsed = extractJson(raw) as { questions?: unknown };
    const questions = parsed.questions;

    if (!Array.isArray(questions) || questions.length === 0) {
      return res.status(500).json({
        success: false,
        message: 'LLM 응답에 questions 배열이 없습니다.',
      });
    }

    const VALID_PRIORITY = ['높음', '보통', '낮음'] as const;
    type Priority = typeof VALID_PRIORITY[number];

    const normalized = questions.slice(0, 10).map((item, i) => {
      if (typeof item === 'string') {
        return { no: i + 1, category: '', question: item, priority: '보통' as Priority, tip: '' };
      }
      const o = item as { category?: string; question?: string; priority?: string; tip?: string };
      const rawPriority = String(o.priority ?? '보통');
      const priority: Priority = (VALID_PRIORITY as readonly string[]).includes(rawPriority)
        ? rawPriority as Priority
        : '보통';
      return {
        no:       i + 1,
        category: String(o.category ?? ''),
        question: String(o.question ?? ''),
        priority,
        tip:      String(o.tip ?? ''),
      };
    });

    return res.json({ success: true, questions: normalized, source });
  } catch (e) {
    console.error('[ai-interview] error:', e);
    return res.status(500).json({
      success: false,
      message: (e as Error).message,
    });
  }
});

export default router;
