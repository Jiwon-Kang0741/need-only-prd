/**
 * POST /api/generate-interview-result
 *
 * [Interview Result Pipeline]
 * STEP 1.  generateInterviewNotes           — LLM으로 InterviewNote.md 작성
 * STEP 1.5 extractStructuredDataFromRawText — (rawText 모드 전용) LLM으로 인터뷰 전문 →
 *                                             keep/change/add/tbd 구조화 데이터 추출
 * STEP 2.  mergeInterviewData               — 답변을 구조화된 JSON으로 병합
 * STEP 3.  matchAndMergeIntoAnnotations     — LLM 매칭으로 @id 주석에 인터뷰 결과 병합 (template)
 * STEP 4.  generateCommentsFromJSON         — script 상단에 전체 요약 블록 주입
 * STEP 5.  saveSpecSourceFiles              — src/spec-source/[screenName]/ 에 원자 저장
 *
 * 실행 조건 (둘 중 하나):
 *   A) 모든 질문에 답변이 있어야 함 (interviewStatus == INTERVIEW_COMPLETED)
 *   B) rawInterviewText 필드에 인터뷰 전문(raw text)을 제공한 경우 — 개별 질문 답변 불필요
 *      → STEP 1.5에서 LLM이 자동으로 구조화 분류 후 @id 주석에 인터뷰 결과 병합
 */
import express, { Request, Response } from 'express';
import fs from 'fs';
import path from 'path';

import { callLLM } from '../utils/llmClient';
import { PATHS, ensureDir } from '../utils/paths';
import { stripInterviewSidePanel } from '../utils/stripSidePanel';

const router = express.Router();

const SPEC_SOURCE_DIR     = path.join(PATHS.projectRoot, 'src', 'spec-source');
const INTERVIEW_NOTES_TPL = path.join(PATHS.projectRoot, 'RequirementPrompt', 'interviewNotes.md');

// ─────────────────────────────────────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────────────────────────────────────
interface QuestionItem {
  no: number;
  category: string;
  question: string;
  priority: string;
  tip?: string;
  answer: string;
}

interface CustomQA {
  question: string;
  answer: string;
}

interface InterviewResultRequest {
  screenName:          string;
  pageName:            string;
  title:               string;
  pageType?:           string;
  questions?:          QuestionItem[];
  customQAs?:          CustomQA[];
  annotationMarkdown?: string;
  /** 인터뷰 전문(raw text) — 제공 시 개별 questions 답변 없이도 파이프라인 실행 가능 */
  rawInterviewText?:   string;
}

type PipelineLog = Record<string, unknown>;

// ─────────────────────────────────────────────────────────────────────────────
//  STEP 1: generateInterviewNotes
// ─────────────────────────────────────────────────────────────────────────────
async function generateInterviewNotes(data: InterviewResultRequest): Promise<string> {
  const template = fs.existsSync(INTERVIEW_NOTES_TPL)
    ? fs.readFileSync(INTERVIEW_NOTES_TPL, 'utf-8')
    : '';

  // rawInterviewText 모드: 개별 questions 대신 전문(raw text) 사용
  let qaText: string;
  if (data.rawInterviewText?.trim()) {
    qaText = data.rawInterviewText.trim();
  } else {
    qaText = (data.questions ?? [])
      .map(q =>
        `Q${q.no} [${q.category}/${q.priority}]: ${q.question}\n` +
        `  설계가설: ${q.tip ?? '없음'}\n` +
        `  답변: ${q.answer}`,
      )
      .join('\n\n');
  }

  const customText = data.customQAs?.length
    ? '\n\n[현장 추가 질문]\n' +
      data.customQAs
        .map((qa, i) => `추가${i + 1}: ${qa.question || '(질문 없음)'}\n  답변: ${qa.answer || '(미작성)'}`)
        .join('\n\n')
    : '';

  const qaLabel = data.rawInterviewText?.trim() ? '인터뷰 전문(Raw Text)' : '인터뷰 Q&A 데이터';

  const prompt =
    `당신은 엔터프라이즈 시스템 전문 IT 비즈니스 분석가(BA)입니다.\n\n` +
    `아래 [${qaLabel}]를 분석하여, 주어진 [InterviewNote 템플릿]을 정확히 채워주세요.\n\n` +
    `규칙 (TEMPLATE LOCK — 절대 준수):\n` +
    `- 템플릿 섹션 구조·순서·마크다운 포맷을 절대 변경하지 마세요.\n` +
    `- 각 답변을 분류 기준(Keep/Change/Add/Out of Scope/TBD)에 따라 정확히 배치하세요.\n` +
    `- 모든 항목에 고유한 @id를 부여하세요 (KEEP-001, CHG-001, ADD-001, OUT-001, TBD-001 형식).\n` +
    `- DataSpec에는 해당 화면의 필드별 기술 명세를 포함하세요.\n` +
    `- BusinessRules에는 정렬/페이징/권한/유효성 규칙을 포함하세요.\n` +
    `- API Specification에는 인터뷰 결과로 도출되는 API 엔드포인트 목록을 작성하세요:\n` +
    `  - @id는 API-001 형식, method는 GET/POST/PUT/PATCH/DELETE 중 하나.\n` +
    `  - requestParams는 "파라미터명(타입, operator)" 형식으로 나열.\n` +
    `  - responseFields는 "필드명(타입)" 형식으로 나열.\n` +
    `  - relatedIds는 관련된 Keep/Change/Add/TBD @id를 쉼표로 나열.\n` +
    `  - 화면 유형에 따라 필요한 모든 API를 빠짐없이 도출하세요 (목록조회, 상세조회, 등록, 수정, 삭제, 코드조회 등).\n` +
    `- 빈 섹션에는 해당 없음 행을 채우세요.\n` +
    `- 자유 서술 최소화, 반드시 구조화된 값을 사용하세요.\n\n` +
    `[화면 정보]\n` +
    `- 화면명: ${data.title}\n` +
    `- 화면 ID: SCR_${data.screenName.toUpperCase()}_001\n` +
    `- 인터뷰 일자: ${new Date().toISOString().split('T')[0]}\n\n` +
    `[${qaLabel}]\n${qaText}${customText}\n\n` +
    `[InterviewNote 템플릿]\n${template}\n\n` +
    `위 템플릿 구조를 100% 유지하면서, 인터뷰 데이터를 바탕으로 모든 섹션을 채워 완성된 InterviewNote.md를 출력하세요.`;

  const result = await callLLM(
    [
      {
        role: 'system',
        content:
          '당신은 InterviewNote 템플릿을 정확히 채우는 BA 전문가입니다. 템플릿 구조를 절대 변경하지 마세요. 섹션 순서와 마크다운 포맷을 100% 유지하세요.',
      },
      { role: 'user', content: prompt },
    ],
    6000,
  );

  return result;
}

// ─────────────────────────────────────────────────────────────────────────────
//  STEP 1.5: extractStructuredDataFromRawText  (rawInterviewText 모드 전용)
//  LLM으로 인터뷰 전문 → keep / change / add / tbd 구조화 데이터 추출
// ─────────────────────────────────────────────────────────────────────────────
interface StructuredKeep   { id: string; name: string; detail: string }
interface StructuredChange { id: string; name: string; asIs: string; toBe: string; rule: string }
interface StructuredAdd    { id: string; name: string; detail: string }
interface StructuredTbd    { id: string; name: string; reason: string }

interface ExtractedStructuredData {
  keep:   StructuredKeep[];
  change: StructuredChange[];
  add:    StructuredAdd[];
  tbd:    StructuredTbd[];
}

async function extractStructuredDataFromRawText(
  rawText: string,
  title: string,
): Promise<ExtractedStructuredData> {
  const prompt =
    `아래 [인터뷰 전문]을 분석하여, 각 답변을 Keep/Change/Add/TBD 카테고리로 분류하고 JSON으로만 반환하세요.\n\n` +
    `[화면 정보] 화면명: ${title}\n\n` +
    `[분류 기준]\n` +
    `- Keep   : 현행 설계/정책을 그대로 유지하거나 확정된 내용\n` +
    `- Change : 현행 대비 수정/변경이 필요하다고 확인된 내용\n` +
    `- Add    : 신규로 추가해야 할 기능/규칙/요구사항\n` +
    `- TBD    : 미결정 또는 추가 확인이 필요한 내용\n\n` +
    `[출력 형식 — 다른 텍스트 없이 JSON 객체만]\n` +
    `{\n` +
    `  "keep":   [{"id":"KEEP-001","name":"요약명(30자 이내)","detail":"상세 내용"}],\n` +
    `  "change": [{"id":"CHG-001","name":"요약명","asIs":"변경 전","toBe":"변경 후","rule":"관련 규칙"}],\n` +
    `  "add":    [{"id":"ADD-001","name":"요약명","detail":"상세 내용"}],\n` +
    `  "tbd":    [{"id":"TBD-001","name":"요약명","reason":"미결 사유"}]\n` +
    `}\n\n` +
    `[인터뷰 전문]\n${rawText}`;

  const raw = await callLLM(
    [
      {
        role: 'system',
        content:
          '인터뷰 내용을 Keep/Change/Add/TBD로 분류하는 BA 전문가입니다. JSON 객체만 반환하고 마크다운 코드블럭을 사용하지 마세요.',
      },
      { role: 'user', content: prompt },
    ],
    3000,
  );

  try {
    const objStart = raw.indexOf('{');
    const objEnd   = raw.lastIndexOf('}');
    if (objStart !== -1 && objEnd !== -1) {
      const parsed = JSON.parse(raw.slice(objStart, objEnd + 1)) as Partial<ExtractedStructuredData>;
      return {
        keep:   Array.isArray(parsed.keep)   ? parsed.keep   : [],
        change: Array.isArray(parsed.change) ? parsed.change : [],
        add:    Array.isArray(parsed.add)    ? parsed.add    : [],
        tbd:    Array.isArray(parsed.tbd)    ? parsed.tbd    : [],
      };
    }
  } catch {
    console.warn('[interview-result] STEP 1.5: 구조화 데이터 파싱 실패, 빈 데이터로 계속');
  }

  return { keep: [], change: [], add: [], tbd: [] };
}

// ─────────────────────────────────────────────────────────────────────────────
//  STEP 2: mergeInterviewData
// ─────────────────────────────────────────────────────────────────────────────
function mergeInterviewData(
  data:           InterviewResultRequest,
  extracted?:     ExtractedStructuredData,
): Record<string, unknown> {
  const now = new Date().toISOString();
  const toReq = (text: string) => ({ text, source: 'interview', createdAt: now });

  const questions = data.questions ?? [];

  // rawInterviewText 모드: STEP 1.5에서 추출한 구조화 데이터 우선 사용
  if (extracted) {
    const keep   = extracted.keep.map(k => ({ ...k, requirement: toReq(k.detail) }));
    const change = extracted.change.map(c => ({ ...c, requirement: toReq(c.toBe) }));
    const add    = extracted.add.map(a => ({
      ...a,
      priority: 'Mid',
      impact:   '현장 인터뷰 추가 요구',
      requirement: toReq(a.detail),
    }));
    const tbd    = extracted.tbd;
    const idCount = keep.length + change.length + add.length + tbd.length;

    return {
      screenName:       data.screenName,
      title:            data.title,
      pageType:         data.pageType,
      createdAt:        now,
      idCount,
      keep,
      change,
      add,
      outOfScope:       [],
      dataSpec:         [],
      businessRules:    [],
      tbd,
      allQuestions:     questions,
      customQAs:        data.customQAs ?? [],
      rawInterviewText: data.rawInterviewText ?? null,
    };
  }

  // structured 모드: questions 키워드 매칭으로 분류 (기존 로직)
  const seen = new Set<string>();
  const dedup = (text: string) => {
    if (seen.has(text)) return false;
    seen.add(text);
    return true;
  };

  const keep = questions
    .filter(q => q.answer && /유지|맞|확인|그대로|동의|필요|yes|ok/i.test(q.answer))
    .filter(q => dedup(q.answer))
    .map((q, i) => ({
      id:          `KEEP-${String(i + 1).padStart(3, '0')}`,
      name:        q.question.slice(0, 50),
      detail:      q.answer,
      requirement: toReq(q.answer),
    }));

  const change = questions
    .filter(q => q.answer && /변경|수정|다르|바꾸|아니|아닙|조정/i.test(q.answer))
    .filter(q => dedup(q.answer))
    .map((q, i) => ({
      id:          `CHG-${String(i + 1).padStart(3, '0')}`,
      asIs:        q.tip ?? q.question,
      toBe:        q.answer,
      rule:        q.category,
      requirement: toReq(q.answer),
    }));

  const tbd = questions
    .filter(q => !q.answer?.trim() || /추후|미결|tbd|나중|모르|확인 필요/i.test(q.answer))
    .map((q, i) => ({
      id:     `TBD-${String(i + 1).padStart(3, '0')}`,
      name:   q.question.slice(0, 50),
      reason: q.answer?.trim() || '답변 미작성',
    }));

  const add = (data.customQAs ?? [])
    .filter(qa => qa.question || qa.answer)
    .map((qa, i) => ({
      id:          `ADD-${String(i + 1).padStart(3, '0')}`,
      priority:    'Mid',
      name:        qa.question || '현장 추가',
      detail:      qa.answer,
      impact:      '현장 인터뷰 추가 요구',
      requirement: toReq(qa.answer),
    }));

  const idCount = keep.length + change.length + tbd.length + add.length;

  return {
    screenName:       data.screenName,
    title:            data.title,
    pageType:         data.pageType,
    createdAt:        now,
    idCount,
    keep,
    change,
    add,
    outOfScope:       [],
    dataSpec:         [],
    businessRules:    [],
    tbd,
    allQuestions:     questions,
    customQAs:        data.customQAs ?? [],
    rawInterviewText: data.rawInterviewText ?? null,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
//  STEP 3: matchAndMergeIntoAnnotations
//  인터뷰 결과 전체를 LLM에 제공 → @id별 @constraints 도출 → 주석에 기입
// ─────────────────────────────────────────────────────────────────────────────

/** 인터뷰 결과(mergedData)를 LLM이 읽기 좋은 컨텍스트 문자열로 변환 */
function buildInterviewContextFromMergedData(mergedData: Record<string, unknown>): string {
  type Item = { id: string; name: string; detail?: string; toBe?: string; asIs?: string; rule?: string; reason?: string };

  const keep   = (mergedData.keep   as Item[]) ?? [];
  const change = (mergedData.change as Item[]) ?? [];
  const add    = (mergedData.add    as Item[]) ?? [];
  const tbd    = (mergedData.tbd    as Item[]) ?? [];

  const lines: string[] = [];

  if (keep.length) {
    lines.push('[KEEP — 유지/확정 사항]');
    keep.forEach(k => lines.push(`  ${k.id} (${k.name}): ${k.detail ?? ''}`));
  }
  if (change.length) {
    lines.push('[CHANGE — 변경 사항]');
    change.forEach(c => lines.push(`  ${c.id} (${c.name}): ${c.asIs ?? ''} → ${c.toBe ?? ''} (규칙: ${c.rule ?? ''})`));
  }
  if (add.length) {
    lines.push('[ADD — 신규 추가 사항]');
    add.forEach(a => lines.push(`  ${a.id} (${a.name}): ${a.detail ?? ''}`));
  }
  if (tbd.length) {
    lines.push('[TBD — 미결 사항]');
    tbd.forEach(t => lines.push(`  ${t.id} (${t.name}): 미결 사유: ${t.reason ?? ''}`));
  }

  return lines.join('\n');
}

async function matchAndMergeIntoAnnotations(
  vueSource:   string,
  mergedData:  Record<string, unknown>,
): Promise<string> {
  // 1. 템플릿에서 <!-- @id: ... --> 주석 전체 추출
  const annotationRe = /<!--([\s\S]*?)-->/g;
  const annotations: { id: string; full: string; summary: string; note: string }[] = [];
  let m: RegExpExecArray | null;
  // eslint-disable-next-line no-cond-assign
  while ((m = annotationRe.exec(vueSource)) !== null) {
    const body        = m[1];
    const idMatch     = body.match(/@id:\s*([^\n\r]+)/);
    const summaryMatch = body.match(/@summary:\s*([^\n\r]+)/);
    const noteMatch   = body.match(/@note:\s*([^\n\r]+)/);
    if (!idMatch) continue;
    annotations.push({
      id:      idMatch[1].trim(),
      full:    m[0],
      summary: summaryMatch?.[1]?.trim() ?? '',
      note:    noteMatch?.[1]?.trim() ?? '',
    });
  }

  if (!annotations.length) {
    console.log('[interview-result] STEP 3: @id 주석 없음, 건너뜀');
    return vueSource;
  }

  // 2. 인터뷰 결과 컨텍스트 문자열 빌드
  const interviewContext = buildInterviewContextFromMergedData(mergedData);

  const totalItems =
    ((mergedData.keep   as unknown[]) ?? []).length +
    ((mergedData.change as unknown[]) ?? []).length +
    ((mergedData.add    as unknown[]) ?? []).length;

  if (totalItems === 0) {
    console.log('[interview-result] STEP 3: 인터뷰 결과 항목 없음, 건너뜀');
    return vueSource;
  }

  // 3. LLM 호출: @id → @constraints JSON 객체 직접 반환
  const annotationList = annotations
    .map(a => `  "${a.id}": "${a.summary} / ${a.note}"`)
    .join('\n');

  console.log(`[interview-result] STEP 3: @id ${annotations.length}개 × 인터뷰 ${totalItems}개 → @constraints 도출 요청`);

  const raw = await callLLM(
    [
      {
        role: 'system',
        content:
          'UI 요소 주석에 업무 제약사항을 채우는 BA 전문가입니다. ' +
          'JSON 객체만 반환하고 마크다운 코드블럭을 사용하지 마세요.',
      },
      {
        role: 'user',
        content:
          `당신은 엔터프라이즈 시스템 BA 전문가입니다.\n\n` +
          `아래 [인터뷰 결과]를 분석하여, [UI 요소 목록]의 각 @id에 적용되는 업무 제약사항(constraints)을 도출해 주세요.\n\n` +
          `[화면 정보] 화면명: ${String(mergedData.title ?? '')}\n\n` +
          `[인터뷰 결과]\n${interviewContext}\n\n` +
          `[UI 요소 목록 (@id: "summary / note")]\n{\n${annotationList}\n}\n\n` +
          `[출력 규칙]\n` +
          `- 각 @id에 직접 적용되는 인터뷰 기반 제약사항만 작성 (예: 필수 입력, 검색 방식, 허용 범위, 권한 조건 등)\n` +
          `- 해당하는 인터뷰 ID(KEEP-001 등)를 괄호 안에 병기\n` +
          `- 제약사항이 없는 @id는 null\n` +
          `- 한 줄 요약, 100자 이내\n` +
          `- 다른 텍스트 없이 아래 JSON 객체만 반환:\n\n` +
          `{\n  "@id-값": "제약사항 문구 [KEEP-001, CHG-001]",\n  "@id-값2": null\n}`,
      },
    ],
    3000,
  );

  // 4. JSON 파싱
  let constraintMap: Record<string, string | null> = {};
  try {
    const objStart = raw.indexOf('{');
    const objEnd   = raw.lastIndexOf('}');
    if (objStart !== -1 && objEnd !== -1) {
      constraintMap = JSON.parse(raw.slice(objStart, objEnd + 1)) as Record<string, string | null>;
    }
  } catch {
    console.warn('[interview-result] STEP 3: JSON 파싱 실패, 원본 유지');
    return vueSource;
  }

  const nonNullCount = Object.values(constraintMap).filter(v => v != null).length;
  if (nonNullCount === 0) {
    console.log('[interview-result] STEP 3: 적용 가능한 @constraints 없음, 원본 유지');
    return vueSource;
  }

  // 5. 각 <!-- @id --> 주석의 @constraints 필드 업데이트
  let result = vueSource;
  let mergedCount = 0;

  for (const ann of annotations) {
    const value = constraintMap[ann.id];
    if (value === undefined) continue;
    const constraintText = value ?? 'null';

    const existingConstraintRe = /(\s*@constraints:\s*)[^\n\r]*/;

    let updated: string;
    if (existingConstraintRe.test(ann.full)) {
      updated = ann.full.replace(existingConstraintRe, `$1${constraintText}`);
    } else {
      const indent = ann.full.match(/^([ \t]*)/m)?.[1] ?? '  ';
      updated = ann.full.replace(/(\s*)-->$/, `\n${indent}  @constraints: ${constraintText}\n${indent}-->`);
    }

    if (updated !== ann.full) {
      result = result.replace(ann.full, updated);
      mergedCount++;
    }
  }

  console.log(`[interview-result] STEP 3: ${mergedCount}개 @id 주석에 @constraints 기입 완료`);
  return result;
}

// ─────────────────────────────────────────────────────────────────────────────
//  STEP 4: generateCommentsFromJSON  (script 상단 전체 요약 블록)
// ─────────────────────────────────────────────────────────────────────────────
function generateCommentsFromJSON(
  vueSource:   string,
  mergedData:  Record<string, unknown>,
): string {
  const keep   = mergedData.keep   as Array<{ id: string; detail: string }>;
  const change = mergedData.change as Array<{ id: string; toBe: string }>;
  const add    = mergedData.add    as Array<{ id: string; detail: string }>;
  const tbd    = mergedData.tbd    as Array<{ id: string; reason: string }>;

  const lines: string[] = [
    '/**',
    ` * @screen: ${String(mergedData.screenName ?? '')}`,
    ` * @generatedAt: ${new Date().toISOString()}`,
    ` * @pipeline: interview-result-v1`,
    ' *',
  ];

  const append = (
    tag: string,
    items: Array<Record<string, string>>,
    keyA: string,
    keyB: string,
  ) => {
    if (!items?.length) return;
    lines.push(` * @${tag}:`);
    items.forEach(item => {
      lines.push(` *  - @id: ${item.id}`);
      lines.push(` *    @requirement:`);
      const val = (item[keyA] ?? item[keyB] ?? '').replace(/\n/g, ' ').slice(0, 120);
      lines.push(` *      - ${val}`);
    });
    lines.push(' *');
  };

  append('keep',   keep,   'detail', 'detail');
  append('change', change, 'toBe',   'toBe');
  append('add',    add,    'detail', 'detail');

  if (tbd?.length) {
    lines.push(' * @tbd:');
    tbd.forEach(t => {
      lines.push(` *  - @id: ${t.id}`);
      lines.push(` *    @reason: ${t.reason.replace(/\n/g, ' ').slice(0, 80)}`);
    });
    lines.push(' *');
  }

  lines.push(' */');
  const commentBlock = lines.join('\n');

  const MARKER_START = '/* [interview-result:start] */';
  const MARKER_END   = '/* [interview-result:end] */';
  const marked = `${MARKER_START}\n${commentBlock}\n${MARKER_END}`;

  // 기존 주석 블록이 있으면 교체 (원자적 업데이트)
  const existingRe = /\/\* \[interview-result:start\] \*\/[\s\S]*?\/\* \[interview-result:end\] \*\//;
  if (existingRe.test(vueSource)) {
    return vueSource.replace(existingRe, marked);
  }

  // <script ...> 태그 직후에 주입
  return vueSource.replace(/(<script\b[^>]*>)/, `$1\n${marked}`);
}

// ─────────────────────────────────────────────────────────────────────────────
//  STEP 4: saveSpecSourceFiles  (atomic write)
// ─────────────────────────────────────────────────────────────────────────────
function saveSpecSourceFiles(
  screenName: string,
  files: { interviewNote: string; componentVue: string; metadata: Record<string, unknown> },
): string {
  const outDir = path.join(SPEC_SOURCE_DIR, screenName);
  ensureDir(outDir);

  const targets = [
    { tmp: path.join(outDir, '.InterviewNote.tmp.md'),  final: path.join(outDir, 'InterviewNote.md'),  content: files.interviewNote },
    { tmp: path.join(outDir, '.Component.tmp.vue'),     final: path.join(outDir, 'Component.vue'),     content: files.componentVue },
    { tmp: path.join(outDir, '.metadata.tmp.json'),     final: path.join(outDir, 'metadata.json'),     content: JSON.stringify(files.metadata, null, 2) },
  ];

  // Write all temps first, then rename (atomic)
  targets.forEach(t => fs.writeFileSync(t.tmp, t.content, 'utf-8'));
  targets.forEach(t => fs.renameSync(t.tmp, t.final));

  return `src/spec-source/${screenName}/`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  POST /api/generate-interview-result
// ─────────────────────────────────────────────────────────────────────────────
router.post('/', async (req: Request, res: Response) => {
  const body = req.body as InterviewResultRequest;
  const log: PipelineLog = { startedAt: new Date().toISOString() };

  // ── Precondition check ────────────────────────────────────────────────────
  if (!body.screenName?.trim() || !body.title?.trim()) {
    return res.status(400).json({ success: false, message: 'screenName과 title은 필수입니다.' });
  }

  const hasRawText = !!body.rawInterviewText?.trim();

  if (!hasRawText) {
    // rawInterviewText 없는 경우: 기존 조건 — 모든 질문에 답변 필요
    if (!Array.isArray(body.questions) || body.questions.length === 0) {
      return res.status(400).json({
        success: false,
        message: '인터뷰 질문 데이터가 없습니다. questions 배열 또는 rawInterviewText를 제공하세요.',
      });
    }

    const unanswered = body.questions.filter(q => !q.answer?.trim());
    if (unanswered.length > 0) {
      return res.status(400).json({
        success:         false,
        message:         `인터뷰가 완료되지 않았습니다. 미작성 질문 ${unanswered.length}개가 있습니다.`,
        unansweredCount: unanswered.length,
      });
    }
  }

  log.inputSnapshot = {
    screenName:    body.screenName,
    title:         body.title,
    mode:          hasRawText ? 'rawText' : 'structured',
    questionCount: body.questions?.length ?? 0,
    customCount:   body.customQAs?.length ?? 0,
    rawTextLength: hasRawText ? body.rawInterviewText!.length : 0,
  };

  console.log(`[interview-result] START "${body.title}" (${body.screenName})`);

  try {
    // ── STEP 1 ────────────────────────────────────────────────────────────
    console.log('[interview-result] STEP 1: generateInterviewNotes');
    const interviewNote = await generateInterviewNotes(body);
    log.step1 = { status: 'ok', chars: interviewNote.length };

    // ── STEP 1.5 (rawText 모드 전용) ──────────────────────────────────────
    //  LLM으로 인터뷰 전문 → keep/change/add/tbd 구조화 데이터 추출
    //  → STEP 3 matchAndMergeIntoAnnotations 에서 @interviewRef 주석 삽입에 필요
    let extracted: ExtractedStructuredData | undefined;
    if (hasRawText) {
      console.log('[interview-result] STEP 1.5: extractStructuredDataFromRawText');
      extracted = await extractStructuredDataFromRawText(body.rawInterviewText!, body.title);
      log.step1_5 = {
        status:      'ok',
        keepCount:   extracted.keep.length,
        changeCount: extracted.change.length,
        addCount:    extracted.add.length,
        tbdCount:    extracted.tbd.length,
      };
      console.log(
        `[interview-result] STEP 1.5: keep=${extracted.keep.length} change=${extracted.change.length}` +
        ` add=${extracted.add.length} tbd=${extracted.tbd.length}`,
      );
    }

    // ── STEP 2 ────────────────────────────────────────────────────────────
    console.log('[interview-result] STEP 2: mergeInterviewData');
    const mergedData = mergeInterviewData(body, extracted);
    log.step2 = {
      status:      'ok',
      idCount:     mergedData.idCount,
      keepCount:   (mergedData.keep   as []).length,
      changeCount: (mergedData.change as []).length,
      addCount:    (mergedData.add    as []).length,
      tbdCount:    (mergedData.tbd    as []).length,
    };

    // ── STEP 3 ────────────────────────────────────────────────────────────
    console.log('[interview-result] STEP 3: matchAndMergeIntoAnnotations');
    const vuePath   = path.join(PATHS.pagesGenerated, `${body.pageName}.vue`);
    const vueSource = fs.existsSync(vuePath) ? fs.readFileSync(vuePath, 'utf-8') : '<!-- vue not found -->';
    const mergedAnnotationVue = await matchAndMergeIntoAnnotations(vueSource, mergedData);
    log.step3 = { status: 'ok', vueFound: fs.existsSync(vuePath) };

    // ── STEP 4 ────────────────────────────────────────────────────────────
    console.log('[interview-result] STEP 4: generateCommentsFromJSON');
    const updatedVue = generateCommentsFromJSON(mergedAnnotationVue, mergedData);
    log.step4 = { status: 'ok' };

    // ── STEP 5 ────────────────────────────────────────────────────────────
    console.log('[interview-result] STEP 5: saveSpecSourceFiles');
    const metadata = {
      ...mergedData,
      interviewCompletedAt: new Date().toISOString(),
      pipeline: 'interview-result-v1',
    };
    // spec-source/Component.vue 에는 인터뷰 사이드패널 제거 후 저장
    const componentVue = stripInterviewSidePanel(updatedVue);
    const outputPath = saveSpecSourceFiles(body.screenName, {
      interviewNote,
      componentVue,
      metadata,
    });

    // 원본 pages/generated/[pageName].vue 는 사이드패널 유지 (인터뷰 화면)
    if (fs.existsSync(vuePath)) {
      fs.writeFileSync(vuePath, updatedVue, 'utf-8');
      console.log(`[interview-result] pages/generated/${body.pageName}.vue 업데이트 완료`);
    }

    log.step5 = { status: 'ok', outputPath };
    log.completedAt = new Date().toISOString();

    console.log(`[interview-result] DONE → ${outputPath}`);

    return res.json({ success: true, outputPath, log });
  } catch (e) {
    const err = e as Error;
    console.error('[interview-result] ERROR:', err.message);
    log.error = err.message;
    return res.status(500).json({ success: false, message: err.message, log });
  }
});

export default router;
