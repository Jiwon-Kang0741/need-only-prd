/**
 * POST /api/annotate-constraints
 *
 * spec-source/[screenName]/metadata.json 의 인터뷰 결과(keep/change/add/tbd)를
 * LLM으로 분석하여, pages/generated/[pageName].vue 와
 * spec-source/[screenName]/Component.vue 의 <!-- @id --> 주석에
 * @constraints 필드를 채워 저장한다.
 *
 * Body: { screenName: string, pageName: string }
 */
import express, { Request, Response } from 'express';
import fs from 'fs';
import path from 'path';

import { callLLM } from '../utils/llmClient';
import { stripInterviewSidePanel } from '../utils/stripSidePanel';
import { PATHS } from '../utils/paths';

const router = express.Router();

const SPEC_SOURCE_DIR = path.join(PATHS.projectRoot, 'src', 'spec-source');

// ─────────────────────────────────────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────────────────────────────────────
interface MetadataItem {
  id:      string;
  name:    string;
  detail?: string;
  toBe?:   string;
  asIs?:   string;
  rule?:   string;
  reason?: string;
}

interface Metadata {
  title:    string;
  keep?:    MetadataItem[];
  change?:  MetadataItem[];
  add?:     MetadataItem[];
  tbd?:     MetadataItem[];
}

// ─────────────────────────────────────────────────────────────────────────────
//  @id 주석 추출
// ─────────────────────────────────────────────────────────────────────────────
interface AnnotationEntry {
  id:      string;
  full:    string;  // <!-- ... --> 전체 원문
  summary: string;
  note:    string;
}

function extractAnnotations(source: string): AnnotationEntry[] {
  const re = /<!--([\s\S]*?)-->/g;
  const result: AnnotationEntry[] = [];
  let m: RegExpExecArray | null;
  // eslint-disable-next-line no-cond-assign
  while ((m = re.exec(source)) !== null) {
    const body        = m[1];
    const idMatch     = body.match(/@id:\s*([^\n\r]+)/);
    const summaryMatch = body.match(/@summary:\s*([^\n\r]+)/);
    const noteMatch   = body.match(/@note:\s*([^\n\r]+)/);
    if (!idMatch) continue;
    result.push({
      id:      idMatch[1].trim(),
      full:    m[0],
      summary: summaryMatch?.[1]?.trim() ?? '',
      note:    noteMatch?.[1]?.trim() ?? '',
    });
  }
  return result;
}

// ─────────────────────────────────────────────────────────────────────────────
//  인터뷰 데이터 → LLM 컨텍스트 문자열 변환
// ─────────────────────────────────────────────────────────────────────────────
function buildInterviewContext(meta: Metadata): string {
  const lines: string[] = [];

  const appendItems = (
    label: string,
    items: MetadataItem[] | undefined,
    getDesc: (item: MetadataItem) => string,
  ) => {
    if (!items?.length) return;
    lines.push(`\n[${label}]`);
    items.forEach(item => {
      lines.push(`  ${item.id} (${item.name}): ${getDesc(item)}`);
    });
  };

  appendItems('KEEP — 유지/확정 사항',  meta.keep,   i => i.detail ?? '');
  appendItems('CHANGE — 변경 사항',     meta.change, i => `${i.asIs ?? ''} → ${i.toBe ?? ''} (규칙: ${i.rule ?? ''})`);
  appendItems('ADD — 신규 추가 사항',   meta.add,    i => i.detail ?? '');
  appendItems('TBD — 미결 사항',        meta.tbd,    i => `미결 사유: ${i.reason ?? ''}`);

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────────────
//  LLM 호출: @id → @constraints 매핑 생성
// ─────────────────────────────────────────────────────────────────────────────
async function deriveConstraints(
  annotations: AnnotationEntry[],
  interviewContext: string,
  title: string,
): Promise<Record<string, string>> {
  const annotationList = annotations
    .map(a => `  "${a.id}": "${a.summary} / ${a.note}"`)
    .join('\n');

  const prompt =
    `당신은 엔터프라이즈 시스템 BA 전문가입니다.\n\n` +
    `아래 [인터뷰 결과]를 분석하여, [UI 요소 목록]의 각 @id에 적용되는 업무 제약사항(constraints)을 도출해 주세요.\n\n` +
    `[화면 정보] 화면명: ${title}\n` +
    `\n[인터뷰 결과]\n${interviewContext}\n\n` +
    `[UI 요소 목록 (@id: "summary / note")]\n{\n${annotationList}\n}\n\n` +
    `[출력 규칙]\n` +
    `- 각 @id에 직접 적용되는 인터뷰 기반 제약사항만 작성 (예: 필수 입력, 검색 방식, 허용 범위, 권한 조건 등)\n` +
    `- 해당하는 인터뷰 ID(KEEP-001 등)를 괄호 안에 병기\n` +
    `- 제약사항이 없는 @id는 null\n` +
    `- 한 줄 요약, 100자 이내\n` +
    `- 다른 텍스트 없이 아래 JSON 객체만 반환:\n\n` +
    `{\n  "@id-값": "제약사항 문구 [KEEP-001, CHG-001]",\n  "@id-값2": null\n}`;

  const raw = await callLLM(
    [
      {
        role: 'system',
        content:
          'UI 요소 주석에 업무 제약사항을 채우는 BA 전문가입니다. ' +
          'JSON 객체만 반환하고 마크다운 코드블럭을 사용하지 마세요.',
      },
      { role: 'user', content: prompt },
    ],
    3000,
  );

  try {
    const objStart = raw.indexOf('{');
    const objEnd   = raw.lastIndexOf('}');
    if (objStart !== -1 && objEnd !== -1) {
      return JSON.parse(raw.slice(objStart, objEnd + 1)) as Record<string, string>;
    }
  } catch {
    console.warn('[annotate-constraints] LLM 응답 JSON 파싱 실패');
  }
  return {};
}

// ─────────────────────────────────────────────────────────────────────────────
//  @constraints 필드 업데이트
//  - 기존 @constraints: 줄 있으면 값 교체
//  - 없으면 --> 직전에 삽입
// ─────────────────────────────────────────────────────────────────────────────
function applyConstraints(
  source: string,
  annotations: AnnotationEntry[],
  constraintMap: Record<string, string | null>,
): { result: string; updatedCount: number } {
  let result = source;
  let updatedCount = 0;

  for (const ann of annotations) {
    const value = constraintMap[ann.id];
    if (value === undefined) continue;     // LLM이 언급하지 않은 @id 는 스킵
    const constraintText = value ?? 'null';

    const existingRe = /(\s*@constraints:\s*)[^\n\r]*/;

    let updated: string;
    if (existingRe.test(ann.full)) {
      updated = ann.full.replace(existingRe, `$1${constraintText}`);
    } else {
      // @constraints 줄 없음 → --> 직전에 삽입 (들여쓰기 유지)
      const indent = ann.full.match(/^([ \t]*)/m)?.[1] ?? '  ';
      updated = ann.full.replace(/(\s*)-->$/, `\n${indent}  @constraints: ${constraintText}\n${indent}-->`);
    }

    if (updated !== ann.full) {
      result = result.replace(ann.full, updated);
      updatedCount++;
    }
  }

  return { result, updatedCount };
}

// ─────────────────────────────────────────────────────────────────────────────
//  POST /api/annotate-constraints
// ─────────────────────────────────────────────────────────────────────────────
router.post('/', async (req: Request, res: Response) => {
  const { screenName, pageName } = req.body as { screenName?: string; pageName?: string };

  if (!screenName?.trim() || !pageName?.trim()) {
    return res.status(400).json({ success: false, message: 'screenName과 pageName은 필수입니다.' });
  }

  // ── 파일 경로 확인 ──────────────────────────────────────────────────────
  const metaPath      = path.join(SPEC_SOURCE_DIR, screenName, 'metadata.json');
  const vuePath       = path.join(PATHS.pagesGenerated, `${pageName}.vue`);
  const componentPath = path.join(SPEC_SOURCE_DIR, screenName, 'Component.vue');

  if (!fs.existsSync(metaPath)) {
    return res.status(404).json({ success: false, message: `metadata.json 없음: spec-source/${screenName}/metadata.json` });
  }
  if (!fs.existsSync(vuePath)) {
    return res.status(404).json({ success: false, message: `Vue 파일 없음: src/pages/generated/${pageName}.vue` });
  }

  console.log(`[annotate-constraints] START screen="${screenName}" page="${pageName}"`);

  try {
    // ── 1. metadata.json 읽기 ────────────────────────────────────────────
    const meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8')) as Metadata;
    const interviewContext = buildInterviewContext(meta);

    const totalItems =
      (meta.keep?.length ?? 0) + (meta.change?.length ?? 0) +
      (meta.add?.length ?? 0) + (meta.tbd?.length ?? 0);

    if (totalItems === 0) {
      return res.status(400).json({ success: false, message: '인터뷰 결과 데이터가 없습니다. generate-interview-result를 먼저 실행하세요.' });
    }

    console.log(`[annotate-constraints] 인터뷰 항목 ${totalItems}개 로드 완료`);

    // ── 2. Vue 파일에서 @id 주석 추출 ──────────────────────────────────
    const vueSource  = fs.readFileSync(vuePath, 'utf-8');
    const annotations = extractAnnotations(vueSource);

    if (!annotations.length) {
      return res.status(400).json({ success: false, message: '@id 주석이 없습니다. ai-annotate를 먼저 실행하세요.' });
    }

    console.log(`[annotate-constraints] @id 주석 ${annotations.length}개 발견`);

    // ── 3. LLM 호출: @id → @constraints 매핑 ──────────────────────────
    console.log('[annotate-constraints] LLM 제약사항 도출 중...');
    const constraintMap = await deriveConstraints(annotations, interviewContext, meta.title);
    const nonNullCount  = Object.values(constraintMap).filter(v => v != null).length;
    console.log(`[annotate-constraints] 제약사항 도출 완료: ${nonNullCount}개 @id에 적용`);

    // ── 4. Vue 소스에 @constraints 삽입 ────────────────────────────────
    const { result: updatedVue, updatedCount } = applyConstraints(vueSource, annotations, constraintMap);

    // ── 5. 파일 저장 (pages/generated + spec-source/Component.vue) ────
    fs.writeFileSync(vuePath, updatedVue, 'utf-8');
    console.log(`[annotate-constraints] pages/generated/${pageName}.vue 저장 완료`);

    if (fs.existsSync(componentPath)) {
      // Component.vue: @constraints 적용 후 인터뷰 사이드패널 제거하여 저장
      const componentSource      = fs.readFileSync(componentPath, 'utf-8');
      const componentAnnotations = extractAnnotations(componentSource);
      const { result: withConstraints } = applyConstraints(componentSource, componentAnnotations, constraintMap);
      const updatedComponent = stripInterviewSidePanel(withConstraints);
      fs.writeFileSync(componentPath, updatedComponent, 'utf-8');
      console.log(`[annotate-constraints] spec-source/${screenName}/Component.vue 저장 완료 (사이드패널 제거됨)`);
    }

    console.log(`[annotate-constraints] DONE — ${updatedCount}개 @id 주석 업데이트`);

    return res.json({
      success:      true,
      updatedCount,
      totalAnnotations: annotations.length,
      constraintMap,
    });

  } catch (e) {
    const err = e as Error;
    console.error('[annotate-constraints] ERROR:', err.message);
    return res.status(500).json({ success: false, message: err.message });
  }
});

export default router;
