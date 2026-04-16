import express, { Request, Response } from 'express';

import { callLLM, extractJson } from '../utils/llmClient';

const router = express.Router();

// ─────────────────────────────────────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────────────────────────────────────
interface AiGenerateRequest {
  pageType: 'list' | 'form';
  title: string;
  description?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Prompt Builder
// ─────────────────────────────────────────────────────────────────────────────
function buildPrompt(req: AiGenerateRequest): string {
  const desc = req.description?.trim() ? `\n화면 설명: ${req.description}` : '';

  if (req.pageType === 'list') {
    return `당신은 한국 엔터프라이즈 UI를 설계하는 시니어 개발자 및 DB 아키텍트입니다.
아래 화면 정보를 보고 목록(List) 화면 설계 정보를 응답하세요.

화면 제목: ${req.title}${desc}

반드시 아래 JSON 형식으로만 응답하세요 (코드블록, 설명 없이):
{
  "domain": "화면의도메인명(영문)",
  "searchFields": [
    {
      "key": "camelCase영문키",
      "label": "한글레이블",
      "type": "text|number|date|daterange|select|checkbox",
      "optionsText": "select일 때만 포함",
      "operator": "EQ|LIKE|BETWEEN|IN"
    }
  ],
  "tableColumns": [
    {
      "key": "camelCase영문키",
      "label": "한글헤더명",
      "dataType": "VARCHAR|NUMBER|DATETIME",
      "dataLength": "길이",
      "align": "left|center|right"
    }
  ],
  "mockRows": [
    { "tableColumns의key1": "현실적인샘플값", "tableColumns의key2": "현실적인샘플값" }
  ]
}

규칙:
- searchFields: 3~5개, 실제 업무에서 자주 쓰이는 조회 조건
- tableColumns: 5~8개 (No 컬럼 제외), 목록에 표시할 주요 정보
- key는 반드시 영문 camelCase (한글·공백·특수문자 금지), 실제 DB 컬럼명으로 활용 가능하도록 의미 있게 작성
- operator: text는 주로 LIKE, number/date 단일값은 EQ, 범위는 BETWEEN, select/checkbox는 IN 또는 EQ
- type 중 daterange는 날짜 범위 조회, checkbox는 Y/N 조회에 사용
- type이 select인 경우 반드시 optionsText 필드를 포함하고, 값은 "코드1:라벨1, 코드2:라벨2" 형식으로 작성 (예: "Y:사용, N:미사용")
- type이 select가 아닌 경우 optionsText 필드는 생략
- dataType: 데이터의 성격에 맞는 표준 SQL 타입을 지정 (VARCHAR, NUMBER, DATETIME 등)
- dataLength: VARCHAR는 길이(예: "100"), NUMBER는 정밀도(예: "10,2"), DATETIME은 생략 가능
- align: 텍스트·코드는 left, 숫자·금액은 right, 날짜·상태는 center
- mockRows: 10건, tableColumns의 key와 정확히 일치하는 key로 구성, 한국어 실제 업무 데이터처럼 현실적으로 작성
- 날짜 값은 "2025-01-15" 형식, 숫자는 숫자형 문자열, select는 optionsText에 있는 코드값 사용`;
  }

  return `당신은 한국 엔터프라이즈 UI를 설계하는 시니어 개발자입니다.
아래 화면 정보를 보고 입력/수정(Form) 화면 설계 정보를 응답하세요.

화면 제목: ${req.title}${desc}

반드시 아래 JSON 형식으로만 응답하세요 (코드블록, 설명 없이):
{
  "formFields": [
    {
      "key": "camelCase영문키",
      "label": "한글레이블",
      "type": "text|number|date|select|textarea|checkbox",
      "required": true,
      "optionsText": "select일 때만 포함",
      "validation": {
        "min": "최소값/최소길이",
        "max": "최대값/최대길이",
        "pattern": "정규표현식(필요시)"
      },
      "description": "필드에 대한 비즈니스 설명(Spec 기재용)"
    }
  ]
}

규칙:
- formFields: 5~10개, 실제 업무에서 입력하는 항목
- key는 반드시 영문 camelCase (한글·공백·특수문자 금지), API Request Body의 Key로 직접 사용됨
- required: 필수 입력 여부 (true/false)
- textarea는 긴 텍스트(내용, 메모 등), checkbox는 Y/N 값에 사용
- type이 select인 경우 반드시 optionsText 필드를 포함하고, 값은 "코드1:라벨1, 코드2:라벨2" 형식으로 작성 (예: "1:남성, 2:여성" 또는 "ACTIVE:활성, INACTIVE:비활성")
- type이 select가 아닌 경우 optionsText 필드는 생략
- validation: 실제 업무 규칙을 고려하여 현실적인 숫자나 길이를 제안 (불필요한 항목은 생략 가능)
- description: 이 필드가 비즈니스 로직상 어떤 의미를 갖는지 간략히 서술`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  POST /api/ai-generate
// ─────────────────────────────────────────────────────────────────────────────
router.post('/', async (req: Request, res: Response) => {
  const { pageType, title, description } = req.body as AiGenerateRequest;

  if (!title?.trim()) {
    return res.status(400).json({ success: false, message: '화면 제목(title)은 필수입니다.' });
  }
  if (pageType !== 'list' && pageType !== 'form') {
    return res.status(400).json({ success: false, message: 'pageType 은 list 또는 form 이어야 합니다.' });
  }

  const prompt = buildPrompt({ pageType, title, description });
  console.log(`[ai-generate] ${pageType} / "${title}"`);

  try {
    const raw = await callLLM(
      [
        {
          role: 'system',
          content: '당신은 엔터프라이즈 UI 설계 전문가입니다. 요청한 JSON 형식으로만 답변합니다.',
        },
        { role: 'user', content: prompt },
      ],
      3000,
    );

    console.log('[ai-generate] raw response:', raw.slice(0, 300));

    const parsed = extractJson(raw) as Record<string, unknown>;
    return res.json({ success: true, ...parsed });
  } catch (e) {
    console.error('[ai-generate] error:', e);
    return res.status(500).json({
      success: false,
      message: (e as Error).message,
    });
  }
});

export default router;
