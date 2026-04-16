import express, { Request, Response } from 'express';
import fs from 'fs';
import path from 'path';

import { callLLM, extractJson } from '../utils/llmClient';
import { PATHS } from '../utils/paths';

const router = express.Router();

// ─────────────────────────────────────────────────────────────────────────────
// LLM 프롬프트: 주석 JSON 목록만 반환
// ─────────────────────────────────────────────────────────────────────────────
const ANNOTATION_SYSTEM_PROMPT = `당신은 Vue.js <template>을 분석하여 각 UI 요소에 대한 구조화된 주석 정보를 JSON 배열로 반환하는 분석가입니다.

[출력 형식 (STRICT)]
반드시 아래 JSON 배열만 반환하세요. 다른 텍스트 없이:
[
  {
    "selector": "엘리먼트를 식별할 수 있는 코드 스니펫 (태그+주요속성, 15자 이내)",
    "id": "kebab-case 고유 ID",
    "type": "input | action | display | container",
    "summary": "요소 설명 (20자 이내)",
    "note": "동작 또는 정책 (30자 이내)",
    "model": "v-model 값 또는 null",
    "constraints": "이 요소의 업무 제약사항 (50자 이내) 또는 null"
  }
]

[규칙]
- selector는 해당 요소를 특정할 수 있는 짧은 코드 스니펫 (예: "<button @click=\\"onSearch\\"", "<input v-model=\\"search.name\\"")
- 주요 UI 요소(버튼, 인풋, 셀렉트, 테이블, 주요 div)만 포함 (최대 20개)
- constraints는 코드에서 파악 가능한 유효성 검사/허용 범위/필수 여부 등 제약사항. 파악 불가 시 null
- JSON만 출력, Markdown 코드블럭 금지`;

// ─────────────────────────────────────────────────────────────────────────────
// 주석 항목 타입
// ─────────────────────────────────────────────────────────────────────────────
interface AnnotationItem {
  selector:    string;
  id:          string;
  type:        string;
  summary:     string;
  note:        string;
  model:       string | null;
  constraints: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// 원본 소스에 주석 삽입
// selector로 줄을 찾아 그 바로 위에 HTML 주석을 삽입
// ─────────────────────────────────────────────────────────────────────────────
function injectAnnotations(source: string, annotations: AnnotationItem[]): string {
  const lines = source.split('\n');

  // 삽입 위치 수집 (역순으로 삽입해야 인덱스 밀림 방지)
  const insertions: { lineIdx: number; comment: string }[] = [];

  for (const ann of annotations) {
    const sel = ann.selector?.trim();
    if (!sel) continue;

    // selector의 핵심 키워드 추출 (첫 번째 공백 또는 > 이전)
    const keyword = sel.replace(/^</, '').split(/[\s>]/)[0];
    if (!keyword) continue;

    // 해당 selector를 포함하는 첫 번째 줄 탐색
    const lineIdx = lines.findIndex((line) => {
      if (!line.includes(keyword)) return false;
      // selector의 나머지 부분도 같은 줄에 있는지 확인
      const rest = sel.slice(1).trim(); // < 제거
      return line.includes(rest.slice(0, Math.min(rest.length, 20)));
    });

    if (lineIdx === -1) continue;

    // 이미 삽입 예정인 줄은 중복 제외
    if (insertions.some((ins) => ins.lineIdx === lineIdx)) continue;

    // 들여쓰기 맞추기
    const indent = lines[lineIdx].match(/^(\s*)/)?.[1] ?? '';

    const comment = [
      `${indent}<!--`,
      `${indent}  @id: ${ann.id}`,
      `${indent}  @type: ${ann.type}`,
      `${indent}  @summary: ${ann.summary}`,
      `${indent}  @note: ${ann.note}`,
      `${indent}  @model: ${ann.model ?? 'null'}`,
      `${indent}  @constraints: ${ann.constraints ?? 'null'}`,
      `${indent}-->`,
    ].join('\n');

    insertions.push({ lineIdx, comment });
  }

  // 역순 삽입 (뒤에서부터 삽입해야 앞쪽 인덱스가 밀리지 않음)
  insertions.sort((a, b) => b.lineIdx - a.lineIdx);

  for (const { lineIdx, comment } of insertions) {
    lines.splice(lineIdx, 0, comment);
  }

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────────────
// <template> 섹션만 추출
// ─────────────────────────────────────────────────────────────────────────────
function extractTemplateSection(source: string): string | null {
  const startTag = source.indexOf('<template');
  if (startTag === -1) return null;
  const tagEnd = source.indexOf('>', startTag);
  if (tagEnd === -1) return null;

  let depth = 1;
  let pos = tagEnd + 1;

  while (pos < source.length && depth > 0) {
    const nextOpen  = source.indexOf('<template', pos);
    const nextClose = source.indexOf('</template>', pos);
    if (nextClose === -1) return null;

    if (nextOpen !== -1 && nextOpen < nextClose) {
      depth++;
      pos = nextOpen + 9;
    } else {
      depth--;
      if (depth === 0) {
        return source.slice(startTag, nextClose + '</template>'.length);
      }
      pos = nextClose + 11;
    }
  }
  return null;
}

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/ai-annotate
// ─────────────────────────────────────────────────────────────────────────────
interface AnnotateBody {
  pageName?: string;
  vueSource?: string;
}

router.post('/', async (req: Request, res: Response) => {
  const { pageName, vueSource } = req.body as AnnotateBody;

  let source = typeof vueSource === 'string' ? vueSource.trim() : '';
  let filePath = '';

  if (!source && pageName?.trim()) {
    const safeName = pageName.trim();
    if (!/^[A-Za-z0-9_-]+$/.test(safeName)) {
      return res.status(400).json({ success: false, message: 'pageName은 영문·숫자·하이픈·언더스코어만 허용됩니다.' });
    }
    filePath = path.join(PATHS.pagesGenerated, `${safeName}.vue`);
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ success: false, message: `파일 없음: src/pages/generated/${safeName}.vue` });
    }
    source = fs.readFileSync(filePath, 'utf-8');
  }

  if (!source) {
    return res.status(400).json({ success: false, message: 'vueSource 또는 pageName이 필요합니다.' });
  }

  const templateSection = extractTemplateSection(source);
  if (!templateSection) {
    return res.status(400).json({ success: false, message: '<template> 블록을 찾을 수 없습니다.' });
  }

  // template이 너무 크면 앞 3000자만 분석 (주요 UI 요소는 대부분 초반에 있음)
  const analysisTarget = templateSection.length > 6000
    ? templateSection.slice(0, 6000) + '\n<!-- ... (truncated for analysis) -->'
    : templateSection;

  console.log(`[ai-annotate] ${pageName ?? '(vueSource)'} | template ${templateSection.length}자 → 분석 ${analysisTarget.length}자`);

  try {
    const raw = await callLLM(
      [
        { role: 'system', content: ANNOTATION_SYSTEM_PROMPT },
        { role: 'user',   content: analysisTarget },
      ],
      3000,
    );

    let annotations: AnnotationItem[] = [];
    try {
      const parsed = extractJson(raw) as unknown;
      if (Array.isArray(parsed)) {
        annotations = parsed as AnnotationItem[];
      } else {
        throw new Error('배열이 아님');
      }
    } catch {
      // JSON 파싱 실패 시 배열 직접 탐색
      const arrStart = raw.indexOf('[');
      const arrEnd   = raw.lastIndexOf(']');
      if (arrStart !== -1 && arrEnd !== -1) {
        annotations = JSON.parse(raw.slice(arrStart, arrEnd + 1)) as AnnotationItem[];
      }
    }

    if (!annotations.length) {
      return res.json({ success: false, message: 'LLM이 주석 목록을 반환하지 않았습니다. 원본 파일은 변경되지 않았습니다.' });
    }

    // 원본 소스에 주석 삽입
    const annotatedSource = injectAnnotations(source, annotations);

    if (filePath) {
      fs.writeFileSync(filePath, annotatedSource, 'utf-8');
      console.log(`[ai-annotate] ${annotations.length}개 주석 삽입 완료: ${filePath}`);
    }

    return res.json({ success: true, annotationCount: annotations.length });

  } catch (e) {
    console.error('[ai-annotate] error:', e);
    return res.status(500).json({ success: false, message: (e as Error).message });
  }
});

export default router;
