import express, { Request, Response } from 'express';
import fs from 'fs';
import path from 'path';
import { Project, SyntaxKind } from 'ts-morph';

import { PATHS, ensureDir } from '../utils/paths';

const router = express.Router();

// ─────────────────────────────────────────────────────────────────────────────
//  Types
// ─────────────────────────────────────────────────────────────────────────────
interface SearchFieldOption {
  value: string;
  label: string;
}

interface SearchField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'daterange' | 'select' | 'checkbox';
  options?: SearchFieldOption[];
  optionMode?: 'direct' | 'codeClass';
  codeClass?: string;
}

interface TableColumn {
  key: string;
  label: string;
}

interface FormField {
  key: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'select' | 'textarea' | 'checkbox';
  required?: boolean;
  options?: SearchFieldOption[];
  optionMode?: 'direct' | 'codeClass';
  codeClass?: string;
}

interface InterviewQuestion {
  no: number;
  category?: string;
  question: string;
  priority?: string;
}

interface PageSpec {
  pageType: 'list' | 'detail' | 'form';
  pageName: string;
  routePath: string;
  title: string;
  description?: string;
  searchFields: SearchField[];
  tableColumns: TableColumn[];
  formFields: FormField[];
  actions: string[];
  mockDataCount: number;
  /** AI가 생성한 샘플 데이터 — 제공 시 buildMockRows 대신 사용 */
  mockRows?: Record<string, string>[];
  /** LLM 고객용 가이드 — SFC 상단 HTML 주석으로 삽입 */
  annotationMarkdown?: string;
  /** 인터뷰 질문 — 목업 화면 우측 패널에 표시 */
  interviewQuestions?: InterviewQuestion[];
}

/** 텍스트 노드 / 속성용 이스케이프 */
function escapeHtmlText(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** HTML 주석 본문에서 종료 시퀀스만 무력화 */
function escapeHtmlCommentBody(s: string): string {
  return s.replace(/\-\->/g, '-- >');
}

// ─────────────────────────────────────────────────────────────────────────────
//  Key Sanitizer
//  key를 유효한 JS 식별자로 정규화 (공백→_, 한글·특수문자 제거)
// ─────────────────────────────────────────────────────────────────────────────
function sanitizeKey(raw: string, fallback: string): string {
  if (!raw || !raw.trim()) return fallback;
  // 공백 → 언더스코어, JS 식별자에서 유효하지 않은 문자 제거
  const sanitized = raw
    .trim()
    .replace(/\s+/g, '_')
    .replace(/[^a-zA-Z0-9_$]/g, '');
  // 숫자로 시작하면 _ 접두어 추가
  return /^[0-9]/.test(sanitized) ? `_${sanitized}` : sanitized || fallback;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Mock Data Generator
// ─────────────────────────────────────────────────────────────────────────────
function buildMockRows(columns: TableColumn[], count: number): Record<string, string>[] {
  return Array.from({ length: count }, (_, i) => {
    const row: Record<string, string> = {};
    for (const col of columns) {
      const safeKey = sanitizeKey(col.key, `col${columns.indexOf(col)}`);
      row[safeKey] = `${col.label || safeKey} ${i + 1}`;
    }
    return row;
  });
}

// ─────────────────────────────────────────────────────────────────────────────
//  Vue SFC Generator — list 타입
// ─────────────────────────────────────────────────────────────────────────────
function generateListVue(spec: PageSpec): string {
  const { title, searchFields, tableColumns, actions, mockDataCount, pageName, routePath } = spec;

  // key 정규화: 빈 key 또는 비식별자 key를 안전한 값으로 교체
  const safeSearchFields = searchFields
    .filter(f => f.label?.trim())
    .map((f, i) => ({ ...f, key: sanitizeKey(f.key, `field${i}`) }));

  const safeTableColumns = tableColumns
    .filter(c => c.label?.trim())
    .map((c, i) => ({ ...c, key: sanitizeKey(c.key, `col${i}`) }));

  // AI가 생성한 mockRows가 있으면 그대로 사용, 없으면 프로그래밍 방식으로 생성
  const mockRows: Record<string, string>[] = (() => {
    if (spec.mockRows?.length) {
      // AI 생성 데이터의 key도 안전한 식별자로 정규화
      return spec.mockRows.map(row => {
        const normalized: Record<string, string> = {};
        for (const [k, v] of Object.entries(row)) {
          const safeKey = sanitizeKey(k, k);
          normalized[safeKey] = String(v ?? '');
        }
        return normalized;
      });
    }
    return buildMockRows(safeTableColumns, mockDataCount);
  })();

  /* ── 검색 필드 HTML ── */
  const searchHtml = safeSearchFields.map(f => {
    if (f.type === 'select') {
      if (f.optionMode === 'codeClass' && f.codeClass) {
        // 공통코드 그룹 참조 — 개발 시 /api/codes/{codeClass} 로 옵션 조회
        return `        <div class="gp-field">
          <label class="gp-label">${f.label}</label>
          <!-- @code_class: ${f.codeClass} — 공통코드 그룹 참조. 개발 시 공통코드 API로 옵션을 조회하여 렌더링하세요. -->
          <select v-model="search.${f.key}" class="gp-select">
            <option value="">전체</option>
          </select>
        </div>`;
      }
      if (f.options?.length) {
        const opts = f.options
          .map(o => `              <option value="${o.value}">${o.label}</option>`)
          .join('\n');
        return `        <div class="gp-field">
          <label class="gp-label">${f.label}</label>
          <select v-model="search.${f.key}" class="gp-select">
            <option value="">전체</option>
${opts}
          </select>
        </div>`;
      }
    }
    if (f.type === 'daterange') {
      return `        <div class="gp-field">
          <label class="gp-label">${f.label}</label>
          <div class="gp-date-range">
            <input v-model="search.${f.key}From" type="date" class="gp-input gp-input--date" />
            <span class="gp-date-sep">~</span>
            <input v-model="search.${f.key}To" type="date" class="gp-input gp-input--date" />
          </div>
        </div>`;
    }
    if (f.type === 'checkbox') {
      return `        <div class="gp-field gp-field--inline">
          <input v-model="search.${f.key}" type="checkbox" id="sch_${f.key}" class="gp-checkbox" />
          <label class="gp-label gp-label--cb" for="sch_${f.key}">${f.label}</label>
        </div>`;
    }
    const iType = f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text';
    return `        <div class="gp-field">
          <label class="gp-label">${f.label}</label>
          <input v-model="search.${f.key}" type="${iType}" class="gp-input" placeholder="${f.label}" />
        </div>`;
  }).join('\n');

  /* ── 액션 버튼 HTML ── */
  const actionBtnMap: Record<string, string> = {
    create: `      <button class="gp-btn gp-btn--primary" @click="() => {}">등록</button>`,
    excel:  `      <button class="gp-btn gp-btn--outline" @click="() => {}">엑셀 다운로드</button>`,
    detail: `      <button class="gp-btn gp-btn--outline" @click="() => {}">상세</button>`,
    delete: `      <button class="gp-btn gp-btn--danger"  @click="() => {}">삭제</button>`,
  };
  const actionBtns = actions.map(a => actionBtnMap[a] ?? '').filter(Boolean).join('\n');

  /* ── 테이블 컬럼 HTML ── */
  const thHtml = safeTableColumns
    .map(c => `              <th class="gp-th">${c.label}</th>`)
    .join('\n');
  const tdHtml = safeTableColumns
    .map(c => `              <td class="gp-td">{{ row.${c.key} }}</td>`)
    .join('\n');
  const colSpan = safeTableColumns.length + 1;

  /* ── 필터 로직 ── */
  const filterLines = safeSearchFields.flatMap(f => {
    if (f.type === 'daterange') {
      return [
        `    (!search.${f.key}From || String(row.${f.key} ?? '') >= String(search.${f.key}From))`,
        `    (!search.${f.key}To   || String(row.${f.key} ?? '') <= String(search.${f.key}To))`,
      ];
    }
    if (f.type === 'checkbox') {
      return [`    (!search.${f.key} || String(row.${f.key} ?? '') === 'true')`];
    }
    return [`    (!search.${f.key} || String(row.${f.key} ?? '').includes(String(search.${f.key})))`];
  });
  const filterLogic = filterLines.length > 0 ? filterLines.join(' &&\n') : '    true';

  /* ── search 초기값 / 리셋 ── */
  const searchInit = safeSearchFields.flatMap(f => {
    if (f.type === 'daterange') return [`  ${f.key}From: ''`, `  ${f.key}To: ''`];
    if (f.type === 'checkbox')  return [`  ${f.key}: false`];
    return [`  ${f.key}: ''`];
  }).join(',\n');

  const searchReset = safeSearchFields.flatMap(f => {
    if (f.type === 'daterange') return [`  search.${f.key}From = '';`, `  search.${f.key}To = '';`];
    if (f.type === 'checkbox')  return [`  search.${f.key} = false;`];
    return [`  search.${f.key} = '';`];
  }).join('\n');

  const hasCheckboxOrRange = safeSearchFields.some(f => f.type === 'checkbox' || f.type === 'daterange');
  const searchReactiveType = hasCheckboxOrRange ? 'Record<string, string | boolean>' : 'Record<string, string>';

  /* ── search 슬롯 ── */
  const searchSlot = safeSearchFields.length > 0
    ? `
    <template #search>
      <div class="gp-search-bar">
${searchHtml}
        <div class="gp-search-actions">
          <button class="gp-btn gp-btn--primary" @click="onSearch">조회</button>
          <button class="gp-btn gp-btn--outline" @click="onReset">초기화</button>
        </div>
      </div>
    </template>
`
    : '';

  /* ── actions-right 슬롯 ── */
  const actionsSlot = actionBtns
    ? `
    <template #actions-right>
${actionBtns}
    </template>
`
    : '';

  const interviewQs = spec.interviewQuestions ?? [];
  const hasSidePanel = interviewQs.length > 0;
  const questionsItemsHtml = interviewQs
    .map((q, idx) => {
      const rawP = String(q.priority ?? 'medium').toLowerCase();
      const priLabel = rawP === 'high' ? '높음' : rawP === 'low' ? '낮음' : '보통';
      const priClass = rawP === 'high' ? 'high' : rawP === 'low' ? 'low' : 'mid';
      const cat = q.category?.trim()
        ? `<span class="gp-side-cat">${escapeHtmlText(q.category)}</span>`
        : '';
      return `      <li class="gp-side-item">
        <div class="gp-side-meta">${cat}<span class="gp-side-pri gp-side-pri--${priClass}">${priLabel}</span></div>
        <p class="gp-side-q">${escapeHtmlText(q.question)}</p>
        <textarea v-model="answers[${idx}]" class="gp-side-answer" placeholder="답변을 입력하세요..." rows="3" />
      </li>`;
    })
    .join('\n');

  const splitOpen = hasSidePanel
    ? `<!-- [interview-side:template-open] -->  <div class="gp-page-split">
    <div class="gp-page-split__main">
`
    : '';

  const answerQsJs = interviewQs
    .map((q, i) => `  '${escapeHtmlText(q.question).replace(/'/g, "\\'")}',`)
    .join('\n');

  const questionMetaJs = interviewQs
    .map((q, i) => {
      const cat  = (q.category ?? '').replace(/'/g, "\\'");
      const ques = escapeHtmlText(q.question).replace(/'/g, "\\'");
      const pri  = (q.priority  ?? 'medium').replace(/'/g, "\\'");
      return `  { no: ${i + 1}, category: '${cat}', question: '${ques}', priority: '${pri}', tip: '' },`;
    })
    .join('\n');

  const splitClose = hasSidePanel
    ? `<!-- [interview-side:template-close] -->    </div>
    <aside class="gp-page-split__side" aria-label="요구사항 인터뷰 질문지">
      <div class="gp-side-header">
        <h3 class="gp-side-title">요구사항 인터뷰 질문지</h3>
        <div class="gp-side-header-actions">
          <button class="gp-side-add-btn" @click="addQA">+ 질문 추가</button>
          <button class="gp-side-copy-btn" :class="{ 'gp-side-copy-btn--done': answerCopied }" @click="copyAnswers">
            {{ answerCopied ? '복사됨!' : '전체 복사' }}
          </button>
        </div>
      </div>
      <ol class="gp-side-list">
${questionsItemsHtml}
      </ol>
      <div v-if="customQAs.length" class="gp-side-custom">
        <div class="gp-side-custom-divider">현장 추가 질문</div>
        <ol class="gp-side-list gp-side-list--custom">
          <li v-for="(item, i) in customQAs" :key="i" class="gp-side-item gp-side-item--custom">
            <div class="gp-side-custom-q-row">
              <input v-model="item.question" class="gp-side-custom-q-input" placeholder="질문을 입력하세요..." />
              <button class="gp-side-del-btn" title="삭제" @click="removeQA(i)">✕</button>
            </div>
            <textarea v-model="item.answer" class="gp-side-answer" placeholder="답변을 입력하세요..." rows="3" />
          </li>
        </ol>
      </div>
      <div v-else class="gp-side-custom-empty">
        <button class="gp-side-add-btn gp-side-add-btn--ghost" @click="addQA">+ 현장 질문 추가</button>
      </div>

      <!-- 인터뷰 결과 붙여넣기 모달 -->
      <div v-if="pasteModalOpen" class="gp-paste-overlay" @click.self="pasteModalOpen = false">
        <div class="gp-paste-modal">
          <div class="gp-paste-modal-header">
            <h4 class="gp-paste-modal-title">인터뷰 결과 붙여넣기</h4>
            <button class="gp-paste-modal-close" @click="pasteModalOpen = false">✕</button>
          </div>
          <p class="gp-paste-modal-desc">현장 인터뷰 메모 또는 회의록을 붙여넣으세요.<br>저장 후 <strong>인터뷰결과생성</strong> 버튼으로 Spec을 생성할 수 있습니다.</p>
          <textarea v-model="pasteText" class="gp-paste-textarea" rows="18" placeholder="인터뷰 결과 내용을 붙여넣으세요..." />
          <div class="gp-paste-modal-footer">
            <button class="gp-paste-cancel-btn" @click="pasteModalOpen = false">취소</button>
            <button class="gp-paste-save-btn" :disabled="!pasteText.trim()" @click="savePastedText">저장</button>
          </div>
        </div>
      </div>

      <!-- 인터뷰결과생성 -->
      <div class="gp-side-result-area">
        <div v-if="resultStatus === 'success'" class="gp-side-result-msg gp-side-result-msg--ok">
          ✓ InterviewNote.md 생성 완료<br>
          <small>src/spec-source/${spec.pageName}/</small>
        </div>
        <div v-else-if="resultStatus === 'error'" class="gp-side-result-msg gp-side-result-msg--err">
          {{ resultMessage }}
        </div>
        <div v-if="pasteConfirmed" class="gp-paste-confirmed">
          ✓ 붙여넣기 결과 등록됨 — 인터뷰결과생성을 실행하세요
          <button class="gp-paste-reset-btn" @click="pasteConfirmed = false; pasteText = ''">초기화</button>
        </div>
        <button class="gp-side-paste-btn" @click="pasteModalOpen = true">
          {{ pasteConfirmed ? '붙여넣기 내용 수정' : '인터뷰 결과 붙여넣기' }}
        </button>
        <button
          class="gp-side-generate-btn"
          :class="{ 'gp-side-generate-btn--ready': interviewCompleted }"
          :disabled="resultGenerating || !interviewCompleted"
          @click="generateInterviewResult"
        >
          {{ resultGenerating ? '생성 중...' : '인터뷰결과생성' }}
        </button>
        <p v-if="!interviewCompleted" class="gp-side-generate-hint">
          모든 질문에 답변을 작성하거나 인터뷰 결과를 붙여넣으세요.
        </p>
      </div>
    </aside>
  </div>
<!-- [interview-side:template-close-end] -->
`
    : '';

  const headLine = `<!-- Generated by MockUp Builder | ${title} (${pageName}) | route: ${routePath} | ${new Date().toISOString()} -->`;
  const guideComment = spec.annotationMarkdown?.trim()
    ? `\n<!--\n=== 고객용 화면 가이드 (LLM) ===\n${escapeHtmlCommentBody(spec.annotationMarkdown)}\n-->\n`
    : '';

  return `${headLine}${guideComment}
<template>
${splitOpen}  <StandardListTemplate>

    <template #title>
      <h2 class="gp-page-title">${title}</h2>
    </template>
${searchSlot}${actionsSlot}
    <template #default>
      <div class="gp-table-wrap">
        <table class="gp-table">
          <thead>
            <tr>
              <th class="gp-th" style="width:50px">No</th>
${thHtml}
            </tr>
          </thead>
          <tbody>
            <tr v-if="!pagedRows.length">
              <td :colspan="${colSpan}" class="gp-td gp-td--empty">조회 결과가 없습니다.</td>
            </tr>
            <tr v-for="(row, i) in pagedRows" :key="i" class="gp-tr">
              <td class="gp-td">{{ (page - 1) * PAGE_SIZE + i + 1 }}</td>
${tdHtml}
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <template #pagination>
      <div class="gp-pagination">
        <button class="gp-btn gp-btn--outline" :disabled="page <= 1" @click="page--">이전</button>
        <span class="gp-pagination__info">{{ page }} / {{ totalPages }} (총 {{ filteredRows.length }}건)</span>
        <button class="gp-btn gp-btn--outline" :disabled="page >= totalPages" @click="page++">다음</button>
      </div>
    </template>

  </StandardListTemplate>
${splitClose}</template>

<script lang="ts" setup>
import { ref, computed, reactive } from 'vue';
import { StandardListTemplate } from '@/components/templates';

${hasSidePanel ? `/* [interview-side:script-start] */
const INTERVIEW_RESULT_API = 'http://localhost:4000/api/generate-interview-result';
const answers = ref<string[]>(Array(${interviewQs.length}).fill(''));
const answerCopied = ref(false);
interface CustomQA { question: string; answer: string; }
const customQAs = ref<CustomQA[]>([]);
const resultGenerating = ref(false);
const resultStatus = ref<'' | 'success' | 'error'>('');
const resultMessage = ref('');
const pasteModalOpen = ref(false);
const pasteText = ref('');
const pasteConfirmed = ref(false);
const interviewCompleted = computed(() =>
  pasteConfirmed.value || answers.value.every(a => a.trim() !== '')
);
const INTERVIEW_QUESTIONS = [
${answerQsJs}
];
const QUESTION_META = [
${questionMetaJs}
];
function addQA() { customQAs.value.push({ question: '', answer: '' }); }
function removeQA(idx: number) { customQAs.value.splice(idx, 1); }
function savePastedText() { pasteConfirmed.value = true; pasteModalOpen.value = false; }
function copyAnswers() {
  const fixed = INTERVIEW_QUESTIONS.map((q, i) => \`Q\${i + 1}. \${q}\\nA: \${answers.value[i] || '(미작성)'}\`).join('\\n\\n');
  const custom = customQAs.value.length
    ? '\\n\\n── 현장 추가 질문 ──\\n\\n' + customQAs.value.map((qa, i) => \`추가\${i + 1}. \${qa.question || '(질문 없음)'}\\nA: \${qa.answer || '(미작성)'}\`).join('\\n\\n')
    : '';
  const text = fixed + custom;
  navigator.clipboard.writeText(text).then(() => {
    answerCopied.value = true; setTimeout(() => { answerCopied.value = false; }, 2000);
  }).catch(() => {
    const el = document.createElement('textarea'); el.value = text;
    document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el);
    answerCopied.value = true; setTimeout(() => { answerCopied.value = false; }, 2000);
  });
}
async function generateInterviewResult() {
  if (!interviewCompleted.value || resultGenerating.value) return;
  resultGenerating.value = true;
  resultStatus.value = '';
  resultMessage.value = '';
  try {
    const questions = QUESTION_META.map((m, i) => ({ ...m, answer: answers.value[i] ?? '' }));
    const payload: Record<string, unknown> = {
      screenName: '${spec.pageName}',
      pageName:   '${spec.pageName}',
      title:      '${escapeHtmlText(spec.title || spec.pageName)}',
      pageType:   '${spec.pageType}',
      questions,
      customQAs:  customQAs.value,
    };
    if (pasteConfirmed.value && pasteText.value.trim()) {
      payload.rawInterviewText = pasteText.value.trim();
    }
    const res = await fetch(INTERVIEW_RESULT_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.success) {
      resultStatus.value = 'success';
      // need-only-prd 통합: 부모 React 앱에 완료 알림 → 자동 spec.md 생성
      try {
        const msg = {
          type: 'pfy-interview-result-success',
          screenName: payload.screenName,
          pageName: payload.pageName,
          title: payload.title,
          pageType: payload.pageType,
        };
        console.log('[generated page] postMessage →', msg, 'isInIframe=', window.parent !== window);
        window.parent?.postMessage(msg, '*');
      } catch (e) { console.warn('[generated page] postMessage 실패:', e); }
    }
    else { resultStatus.value = 'error'; resultMessage.value = data.message ?? '생성에 실패했습니다.'; }
  } catch (e) {
    resultStatus.value = 'error';
    resultMessage.value = \`요청 실패: \${(e as Error).message}\`;
  } finally {
    resultGenerating.value = false;
  }
}
/* [interview-side:script-end] */` : ''}

const PAGE_SIZE = 10;
const page = ref(1);

const search = reactive<${searchReactiveType}>({
${searchInit}
});

const MOCK_DATA: Record<string, string>[] = ${JSON.stringify(mockRows, null, 2)};

const filteredRows = computed(() =>
  MOCK_DATA.filter(row =>
${filterLogic}
  ),
);

const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredRows.value.length / PAGE_SIZE)),
);

const pagedRows = computed(() =>
  filteredRows.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE),
);

function onSearch() {
  page.value = 1;
}

function onReset() {
${searchReset}
  page.value = 1;
}
</script>

<style scoped>
.gp-page-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--txt-color-1);
  margin: 0;
}

/* ── 검색 바 ── */
.gp-search-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-2);
  border: 1px solid var(--divider-1);
  border-radius: 6px;
}

.gp-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.gp-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--txt-color-3);
}

.gp-search-actions {
  display: flex;
  gap: 6px;
  padding-top: 14px;
}

.gp-field--inline {
  flex-direction: row;
  align-items: center;
  padding-top: 18px;
  gap: 6px;
}

.gp-date-range {
  display: flex;
  align-items: center;
  gap: 6px;
}

.gp-date-sep {
  color: var(--txt-color-3);
  font-size: 13px;
}

.gp-input--date {
  min-width: 120px;
  max-width: 140px;
}

.gp-label--cb {
  padding-top: 0;
  font-size: 13px;
  color: var(--txt-color-1);
  cursor: pointer;
}

.gp-checkbox {
  width: 15px;
  height: 15px;
  cursor: pointer;
  accent-color: var(--brand-secondary-color);
}

.gp-input,
.gp-select {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--divider-2);
  border-radius: 4px;
  font-size: 13px;
  background: var(--bg-1);
  color: var(--txt-color-1);
  outline: none;
  min-width: 140px;
}
.gp-input:focus,
.gp-select:focus {
  border-color: var(--brand-secondary-color);
}

/* ── 버튼 ── */
.gp-btn {
  height: 32px;
  padding: 0 14px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: opacity 0.15s;
}
.gp-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.gp-btn--primary { background: var(--brand-secondary-color); color: #fff; border-color: var(--brand-secondary-color); }
.gp-btn--outline { background: var(--bg-1); border-color: var(--divider-2); color: var(--txt-color-2); }
.gp-btn--danger  { background: #ef4444; color: #fff; border-color: #ef4444; }

/* ── 테이블 ── */
.gp-table-wrap {
  width: 100%;
  height: 100%;
  overflow: auto;
}

.gp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.gp-th {
  background: var(--bg-2);
  color: var(--txt-color-2);
  font-weight: 600;
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid var(--divider-2);
  white-space: nowrap;
  position: sticky;
  top: 0;
  z-index: 1;
}

.gp-td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--divider-1);
  color: var(--txt-color-1);
}
.gp-td--empty {
  text-align: center;
  color: var(--txt-color-4);
  padding: 48px 0;
}

.gp-tr:hover { background: var(--bg-2); }

/* ── 페이지네이션 ── */
.gp-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 8px 0;
}

.gp-pagination__info {
  font-size: 13px;
  color: var(--txt-color-3);
}

/* [interview-side:css-start] */
/* ── 목업 + 인터뷰 질문지 분할 ── */
.gp-page-split {
  display: flex;
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  align-items: stretch;
}

.gp-page-split__main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.gp-page-split__main :deep(.std-list) {
  flex: 1;
  min-height: 0;
}

.gp-page-split__side {
  width: min(360px, 38vw);
  flex-shrink: 0;
  border-left: 1px solid var(--divider-1);
  background: var(--bg-2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.gp-side-title {
  flex-shrink: 0;
  margin: 0;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 700;
  color: var(--txt-color-1);
  border-bottom: 1px solid var(--divider-1);
  background: var(--bg-1);
}

.gp-side-list {
  flex: 1;
  margin: 0;
  padding: 10px 12px 14px 28px;
  overflow-y: auto;
  font-size: 12px;
  color: var(--txt-color-2);
  line-height: 1.55;
}

.gp-side-item {
  margin-bottom: 12px;
}

.gp-side-item::marker {
  color: var(--txt-color-4);
  font-weight: 600;
}

.gp-side-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 4px;
}

.gp-side-cat {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-1);
  color: var(--txt-color-3);
  border: 1px solid var(--divider-1);
}

.gp-side-pri {
  font-size: 10px;
  font-weight: 600;
}

.gp-side-pri--high { color: #dc2626; }
.gp-side-pri--mid { color: var(--txt-color-3); }
.gp-side-pri--low { color: var(--txt-color-4); }

.gp-side-q {
  margin: 0 0 6px;
  color: var(--txt-color-1);
  font-size: 12px;
}

/* ── 답변 헤더 ── */
.gp-side-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--divider-1);
  background: var(--bg-1);
}

.gp-side-copy-btn {
  flex-shrink: 0;
  height: 26px;
  padding: 0 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--divider-2);
  background: var(--bg-1);
  color: var(--txt-color-2);
  transition: background 0.15s, color 0.15s;
}

.gp-side-copy-btn:hover { background: var(--bg-2); }
.gp-side-copy-btn--done { background: #f0fdf4; border-color: #bbf7d0; color: #16a34a; }

.gp-side-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.gp-side-add-btn {
  height: 26px;
  padding: 0 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--brand-secondary-color);
  background: var(--bg-1);
  color: var(--brand-secondary-color);
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
}

.gp-side-add-btn:hover { background: var(--brand-secondary-color); color: #fff; }

.gp-side-add-btn--ghost {
  height: 32px;
  padding: 0 14px;
  font-size: 12px;
  border-style: dashed;
}

.gp-side-custom { flex-shrink: 0; border-top: 2px dashed var(--divider-1); }

.gp-side-custom-divider {
  font-size: 11px;
  font-weight: 600;
  color: var(--txt-color-3);
  padding: 8px 14px 4px;
  letter-spacing: 0.03em;
}

.gp-side-list--custom { padding-top: 4px; }

.gp-side-item--custom {
  list-style: none;
  padding: 10px 10px 10px 12px;
  border: 1px solid var(--divider-1);
  border-radius: 6px;
  background: var(--bg-1);
  margin-bottom: 10px;
}

.gp-side-custom-q-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.gp-side-custom-q-input {
  flex: 1;
  min-width: 0;
  height: 30px;
  padding: 0 8px;
  border: 1px solid var(--divider-2);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  color: var(--txt-color-1);
  background: var(--bg-2);
  outline: none;
  transition: border-color 0.15s;
}

.gp-side-custom-q-input:focus { border-color: var(--brand-secondary-color); background: #fff; }
.gp-side-custom-q-input::placeholder { color: var(--txt-color-4); font-weight: 400; }

.gp-side-del-btn {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--txt-color-4);
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}

.gp-side-del-btn:hover { background: #fee2e2; color: #ef4444; }

.gp-side-custom-empty {
  padding: 12px 14px 16px;
  display: flex;
  justify-content: center;
}


/* ── 인터뷰결과생성 영역 ── */
.gp-side-result-area {
  flex-shrink: 0;
  padding: 12px 14px 16px;
  border-top: 2px solid var(--divider-1);
  background: var(--bg-1);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.gp-side-result-msg { font-size: 11px; line-height: 1.5; padding: 8px 10px; border-radius: 5px; }
.gp-side-result-msg--ok  { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.gp-side-result-msg--err { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.gp-side-generate-btn {
  width: 100%; height: 36px; border-radius: 6px; font-size: 13px; font-weight: 700;
  cursor: pointer; border: 1.5px solid var(--divider-2); background: var(--bg-2);
  color: var(--txt-color-3); transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.gp-side-generate-btn--ready { border-color: var(--brand-secondary-color); background: var(--brand-secondary-color); color: #fff; }
.gp-side-generate-btn--ready:hover { opacity: 0.9; }
/* ── 붙여넣기 버튼·모달 ── */
.gp-side-paste-btn {
  width: 100%; padding: 7px 10px; border: 1px dashed #94a3b8; border-radius: 6px;
  background: #f8fafc; cursor: pointer; font-size: 12px; color: #475569;
  transition: all 0.15s; text-align: center;
}
.gp-side-paste-btn:hover { border-color: #3b82f6; color: #3b82f6; background: #eff6ff; }
.gp-paste-confirmed {
  font-size: 11px; color: #16a34a; background: #f0fdf4; border: 1px solid #bbf7d0;
  border-radius: 5px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center;
}
.gp-paste-reset-btn {
  background: none; border: none; cursor: pointer; font-size: 11px; color: #9ca3af; text-decoration: underline;
}
.gp-paste-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}
.gp-paste-modal {
  background: #fff; border-radius: 12px; padding: 24px 28px 20px; width: 580px; max-width: 95vw;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2); display: flex; flex-direction: column; gap: 14px;
}
.gp-paste-modal-header { display: flex; justify-content: space-between; align-items: center; }
.gp-paste-modal-title { margin: 0; font-size: 16px; font-weight: 600; color: #111827; }
.gp-paste-modal-close {
  background: none; border: none; cursor: pointer; font-size: 18px; color: #9ca3af; line-height: 1;
  padding: 2px 6px; border-radius: 4px;
}
.gp-paste-modal-close:hover { color: #374151; background: #f3f4f6; }
.gp-paste-modal-desc { margin: 0; font-size: 13px; color: #6b7280; line-height: 1.6; }
.gp-paste-textarea {
  width: 100%; min-height: 260px; border: 1px solid #d1d5db; border-radius: 8px;
  padding: 12px 14px; font-size: 13px; resize: vertical; font-family: inherit;
  box-sizing: border-box; line-height: 1.7; color: #374151;
}
.gp-paste-textarea:focus { outline: 2px solid #3b82f6; border-color: transparent; }
.gp-paste-modal-footer { display: flex; justify-content: flex-end; gap: 8px; }
.gp-paste-cancel-btn {
  padding: 8px 18px; border: 1px solid #d1d5db; border-radius: 7px;
  background: #fff; cursor: pointer; font-size: 13px; color: #374151;
}
.gp-paste-cancel-btn:hover { background: #f9fafb; }
.gp-paste-save-btn {
  padding: 8px 20px; border: none; border-radius: 7px;
  background: #3b82f6; color: #fff; cursor: pointer; font-size: 13px; font-weight: 600;
}
.gp-paste-save-btn:disabled { background: #9ca3af; cursor: not-allowed; }
.gp-paste-save-btn:not(:disabled):hover { background: #2563eb; }
.gp-side-generate-btn:disabled { cursor: not-allowed; opacity: 0.6; }
.gp-side-generate-hint { margin: 0; font-size: 10px; color: var(--txt-color-4); text-align: center; }
/* ── 답변 입력 ── */
.gp-side-answer {
  display: block;
  width: 100%;
  box-sizing: border-box;
  margin-top: 4px;
  padding: 7px 9px;
  border: 1px solid var(--divider-2);
  border-radius: 5px;
  font-size: 12px;
  font-family: inherit;
  line-height: 1.5;
  color: var(--txt-color-1);
  background: var(--bg-1);
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}

.gp-side-answer:focus {
  border-color: var(--brand-secondary-color);
  background: #fff;
}

.gp-side-answer::placeholder {
  color: var(--txt-color-4);
  font-style: italic;
}
/* [interview-side:css-end] */
</style>
`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Vue SFC Generator — form 타입
// ─────────────────────────────────────────────────────────────────────────────
function generateFormVue(spec: PageSpec): string {
  const { title, description, formFields = [], pageName, routePath } = spec;

  const safeFormFields = formFields
    .filter(f => f.label?.trim())
    .map((f, i) => ({ ...f, key: sanitizeKey(f.key, `field${i}`) }));

  /* ── 폼 필드 HTML ── */
  const fieldHtml = safeFormFields.map(f => {
    const labelClass = f.required ? 'form-label required' : 'form-label';

    if (f.type === 'checkbox') {
      return `          <div class="form-row gp-form-row--cb">
            <label class="${labelClass}">${f.label}</label>
            <div class="form-control gp-cb-control">
              <input v-model="form.${f.key}" type="checkbox" id="form_${f.key}" class="gp-checkbox" />
              <label for="form_${f.key}" class="gp-cb-label">${f.label}</label>
            </div>
          </div>`;
    }

    let controlHtml = '';
    if (f.type === 'textarea') {
      controlHtml = `<textarea v-model="form.${f.key}" class="gp-textarea" rows="4" placeholder="${f.label}"></textarea>`;
    } else if (f.type === 'select') {
      if (f.optionMode === 'codeClass' && f.codeClass) {
        // 공통코드 그룹 참조 — 개발 시 /api/codes/{codeClass} 로 옵션 조회
        controlHtml = `<!-- @code_class: ${f.codeClass} — 공통코드 그룹 참조. 개발 시 공통코드 API로 옵션을 조회하여 렌더링하세요. -->
              <select v-model="form.${f.key}" class="gp-select">
                <option value="">선택하세요</option>
              </select>`;
      } else if (f.options?.length) {
        const opts = f.options
          .map(o => `                <option value="${o.value}">${o.label}</option>`)
          .join('\n');
        controlHtml = `<select v-model="form.${f.key}" class="gp-select">
                <option value="">선택하세요</option>
${opts}
              </select>`;
      } else {
        controlHtml = `<input v-model="form.${f.key}" type="text" class="gp-input" placeholder="${f.label}" />`;
      }
    } else {
      const iType = f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text';
      controlHtml = `<input v-model="form.${f.key}" type="${iType}" class="gp-input" placeholder="${f.label}" />`;
    }

    return `          <div class="form-row">
            <label class="${labelClass}">${f.label}</label>
            <div class="form-control">
              ${controlHtml}
            </div>
          </div>`;
  }).join('\n');

  /* ── TypeScript 인터페이스 및 초기값 ── */
  const formTypeLines = safeFormFields
    .map(f => {
      if (f.type === 'number')   return `  ${f.key}: number;`;
      if (f.type === 'checkbox') return `  ${f.key}: boolean;`;
      return `  ${f.key}: string;`;
    })
    .join('\n');

  const formInitLines = safeFormFields
    .map(f => {
      if (f.type === 'number')   return `  ${f.key}: 0,`;
      if (f.type === 'checkbox') return `  ${f.key}: false,`;
      return `  ${f.key}: '',`;
    })
    .join('\n');

  /* ── description 슬롯 ── */
  const descSlot = description?.trim()
    ? `
    <template #description>
      <p class="gp-description">${description}</p>
    </template>
`
    : '';

  const interviewQsForm = spec.interviewQuestions ?? [];
  const hasSidePanelForm = interviewQsForm.length > 0;
  const questionsItemsHtmlForm = interviewQsForm
    .map((q, idx) => {
      const rawP = String(q.priority ?? 'medium').toLowerCase();
      const priLabel = rawP === 'high' ? '높음' : rawP === 'low' ? '낮음' : '보통';
      const priClass = rawP === 'high' ? 'high' : rawP === 'low' ? 'low' : 'mid';
      const cat = q.category?.trim()
        ? `<span class="gp-side-cat">${escapeHtmlText(q.category)}</span>`
        : '';
      return `      <li class="gp-side-item">
        <div class="gp-side-meta">${cat}<span class="gp-side-pri gp-side-pri--${priClass}">${priLabel}</span></div>
        <p class="gp-side-q">${escapeHtmlText(q.question)}</p>
        <textarea v-model="answers[${idx}]" class="gp-side-answer" placeholder="답변을 입력하세요..." rows="3" />
      </li>`;
    })
    .join('\n');

  const splitOpenForm = hasSidePanelForm
    ? `<!-- [interview-side:template-open] -->  <div class="gp-page-split">
    <div class="gp-page-split__main">
`
    : '';

  const answerQsJsForm = interviewQsForm
    .map(q => `  '${escapeHtmlText(q.question).replace(/'/g, "\\'")}',`)
    .join('\n');

  const questionMetaJsForm = interviewQsForm
    .map((q, i) => {
      const cat  = (q.category ?? '').replace(/'/g, "\\'");
      const ques = escapeHtmlText(q.question).replace(/'/g, "\\'");
      const pri  = (q.priority  ?? 'medium').replace(/'/g, "\\'");
      return `  { no: ${i + 1}, category: '${cat}', question: '${ques}', priority: '${pri}', tip: '' },`;
    })
    .join('\n');

  const splitCloseForm = hasSidePanelForm
    ? `<!-- [interview-side:template-close] -->    </div>
    <aside class="gp-page-split__side" aria-label="요구사항 인터뷰 질문지">
      <div class="gp-side-header">
        <h3 class="gp-side-title">요구사항 인터뷰 질문지</h3>
        <div class="gp-side-header-actions">
          <button class="gp-side-add-btn" @click="addQA">+ 질문 추가</button>
          <button class="gp-side-copy-btn" :class="{ 'gp-side-copy-btn--done': answerCopied }" @click="copyAnswers">
            {{ answerCopied ? '복사됨!' : '전체 복사' }}
          </button>
        </div>
      </div>
      <ol class="gp-side-list">
${questionsItemsHtmlForm}
      </ol>
      <div v-if="customQAs.length" class="gp-side-custom">
        <div class="gp-side-custom-divider">현장 추가 질문</div>
        <ol class="gp-side-list gp-side-list--custom">
          <li v-for="(item, i) in customQAs" :key="i" class="gp-side-item gp-side-item--custom">
            <div class="gp-side-custom-q-row">
              <input v-model="item.question" class="gp-side-custom-q-input" placeholder="질문을 입력하세요..." />
              <button class="gp-side-del-btn" title="삭제" @click="removeQA(i)">✕</button>
            </div>
            <textarea v-model="item.answer" class="gp-side-answer" placeholder="답변을 입력하세요..." rows="3" />
          </li>
        </ol>
      </div>
      <div v-else class="gp-side-custom-empty">
        <button class="gp-side-add-btn gp-side-add-btn--ghost" @click="addQA">+ 현장 질문 추가</button>
      </div>

      <!-- 인터뷰 결과 붙여넣기 모달 -->
      <div v-if="pasteModalOpen" class="gp-paste-overlay" @click.self="pasteModalOpen = false">
        <div class="gp-paste-modal">
          <div class="gp-paste-modal-header">
            <h4 class="gp-paste-modal-title">인터뷰 결과 붙여넣기</h4>
            <button class="gp-paste-modal-close" @click="pasteModalOpen = false">✕</button>
          </div>
          <p class="gp-paste-modal-desc">현장 인터뷰 메모 또는 회의록을 붙여넣으세요.<br>저장 후 <strong>인터뷰결과생성</strong> 버튼으로 Spec을 생성할 수 있습니다.</p>
          <textarea v-model="pasteText" class="gp-paste-textarea" rows="18" placeholder="인터뷰 결과 내용을 붙여넣으세요..." />
          <div class="gp-paste-modal-footer">
            <button class="gp-paste-cancel-btn" @click="pasteModalOpen = false">취소</button>
            <button class="gp-paste-save-btn" :disabled="!pasteText.trim()" @click="savePastedText">저장</button>
          </div>
        </div>
      </div>

      <!-- 인터뷰결과생성 -->
      <div class="gp-side-result-area">
        <div v-if="resultStatus === 'success'" class="gp-side-result-msg gp-side-result-msg--ok">
          ✓ InterviewNote.md 생성 완료<br>
          <small>src/spec-source/${spec.pageName}/</small>
        </div>
        <div v-else-if="resultStatus === 'error'" class="gp-side-result-msg gp-side-result-msg--err">
          {{ resultMessage }}
        </div>
        <div v-if="pasteConfirmed" class="gp-paste-confirmed">
          ✓ 붙여넣기 결과 등록됨 — 인터뷰결과생성을 실행하세요
          <button class="gp-paste-reset-btn" @click="pasteConfirmed = false; pasteText = ''">초기화</button>
        </div>
        <button class="gp-side-paste-btn" @click="pasteModalOpen = true">
          {{ pasteConfirmed ? '붙여넣기 내용 수정' : '인터뷰 결과 붙여넣기' }}
        </button>
        <button
          class="gp-side-generate-btn"
          :class="{ 'gp-side-generate-btn--ready': interviewCompleted }"
          :disabled="resultGenerating || !interviewCompleted"
          @click="generateInterviewResult"
        >
          {{ resultGenerating ? '생성 중...' : '인터뷰결과생성' }}
        </button>
        <p v-if="!interviewCompleted" class="gp-side-generate-hint">
          모든 질문에 답변을 작성하거나 인터뷰 결과를 붙여넣으세요.
        </p>
      </div>
    </aside>
  </div>
<!-- [interview-side:template-close-end] -->
`
    : '';

  const headLineForm = `<!-- Generated by MockUp Builder | ${title} (${pageName}) | route: ${routePath} | ${new Date().toISOString()} -->`;
  const guideCommentForm = spec.annotationMarkdown?.trim()
    ? `\n<!--\n=== 고객용 화면 가이드 (LLM) ===\n${escapeHtmlCommentBody(spec.annotationMarkdown)}\n-->\n`
    : '';

  return `${headLineForm}${guideCommentForm}
<template>
${splitOpenForm}  <StandardEditTemplate>

    <template #title>
      <h2 class="gp-page-title">${title}</h2>
    </template>
${descSlot}
    <template #default>
      <div class="form-section">
        <h3 class="form-section__title">기본 정보</h3>
${fieldHtml || '        <!-- 폼 필드를 추가하세요 -->'}
      </div>
    </template>

    <template #footer-right>
      <button class="gp-btn gp-btn--outline" @click="onCancel">취소</button>
      <button class="gp-btn gp-btn--primary" @click="onSave">저장</button>
    </template>

  </StandardEditTemplate>
${splitCloseForm}</template>

<script lang="ts" setup>
import { reactive${hasSidePanelForm ? `, ref` : ``} } from 'vue';
import { StandardEditTemplate } from '@/components/templates';

${hasSidePanelForm ? `/* [interview-side:script-start] */
const INTERVIEW_RESULT_API = 'http://localhost:4000/api/generate-interview-result';
const answers = ref<string[]>(Array(${interviewQsForm.length}).fill(''));
const answerCopied = ref(false);
interface CustomQA { question: string; answer: string; }
const customQAs = ref<CustomQA[]>([]);
const resultGenerating = ref(false);
const resultStatus = ref<'' | 'success' | 'error'>('');
const resultMessage = ref('');
const pasteModalOpen = ref(false);
const pasteText = ref('');
const pasteConfirmed = ref(false);
const interviewCompleted = computed(() =>
  pasteConfirmed.value || answers.value.every(a => a.trim() !== '')
);
const INTERVIEW_QUESTIONS = [
${answerQsJsForm}
];
const QUESTION_META = [
${questionMetaJsForm}
];
function addQA() { customQAs.value.push({ question: '', answer: '' }); }
function removeQA(idx: number) { customQAs.value.splice(idx, 1); }
function savePastedText() { pasteConfirmed.value = true; pasteModalOpen.value = false; }
function copyAnswers() {
  const fixed = INTERVIEW_QUESTIONS.map((q, i) => \`Q\${i + 1}. \${q}\\nA: \${answers.value[i] || '(미작성)'}\`).join('\\n\\n');
  const custom = customQAs.value.length
    ? '\\n\\n── 현장 추가 질문 ──\\n\\n' + customQAs.value.map((qa, i) => \`추가\${i + 1}. \${qa.question || '(질문 없음)'}\\nA: \${qa.answer || '(미작성)'}\`).join('\\n\\n')
    : '';
  const text = fixed + custom;
  navigator.clipboard.writeText(text).then(() => {
    answerCopied.value = true; setTimeout(() => { answerCopied.value = false; }, 2000);
  }).catch(() => {
    const el = document.createElement('textarea'); el.value = text;
    document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el);
    answerCopied.value = true; setTimeout(() => { answerCopied.value = false; }, 2000);
  });
}
async function generateInterviewResult() {
  if (!interviewCompleted.value || resultGenerating.value) return;
  resultGenerating.value = true;
  resultStatus.value = '';
  resultMessage.value = '';
  try {
    const questions = QUESTION_META.map((m, i) => ({ ...m, answer: answers.value[i] ?? '' }));
    const payload: Record<string, unknown> = {
      screenName: '${spec.pageName}',
      pageName:   '${spec.pageName}',
      title:      '${escapeHtmlText(spec.title || spec.pageName)}',
      pageType:   '${spec.pageType}',
      questions,
      customQAs:  customQAs.value,
    };
    if (pasteConfirmed.value && pasteText.value.trim()) {
      payload.rawInterviewText = pasteText.value.trim();
    }
    const res = await fetch(INTERVIEW_RESULT_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.success) {
      resultStatus.value = 'success';
      // need-only-prd 통합: 부모 React 앱에 완료 알림 → 자동 spec.md 생성
      try {
        const msg = {
          type: 'pfy-interview-result-success',
          screenName: payload.screenName,
          pageName: payload.pageName,
          title: payload.title,
          pageType: payload.pageType,
        };
        console.log('[generated page] postMessage →', msg, 'isInIframe=', window.parent !== window);
        window.parent?.postMessage(msg, '*');
      } catch (e) { console.warn('[generated page] postMessage 실패:', e); }
    }
    else { resultStatus.value = 'error'; resultMessage.value = data.message ?? '생성에 실패했습니다.'; }
  } catch (e) {
    resultStatus.value = 'error';
    resultMessage.value = \`요청 실패: \${(e as Error).message}\`;
  } finally {
    resultGenerating.value = false;
  }
}
/* [interview-side:script-end] */` : ''}

interface FormData {
${formTypeLines || '  // 필드 없음'}
}

const form = reactive<FormData>({
${formInitLines || '  // 필드 없음'}
});

function onSave() {
  console.log('[MockUp] 저장:', JSON.stringify(form, null, 2));
  alert('저장되었습니다. (Mock)');
}

function onCancel() {
  history.back();
}
</script>

<style scoped>
.gp-page-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--txt-color-1);
  margin: 0;
}

.gp-description {
  font-size: 13px;
  color: var(--txt-color-3);
  margin: 0;
}

.gp-input,
.gp-select,
.gp-textarea {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--divider-2);
  border-radius: 4px;
  font-size: 13px;
  background: var(--bg-1);
  color: var(--txt-color-1);
  outline: none;
  box-sizing: border-box;
}
.gp-input:focus,
.gp-select:focus,
.gp-textarea:focus {
  border-color: var(--brand-secondary-color);
}
.gp-textarea {
  resize: vertical;
}

.gp-btn {
  height: 34px;
  padding: 0 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: opacity 0.15s;
}
.gp-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.gp-btn--primary { background: var(--brand-secondary-color); color: #fff; border-color: var(--brand-secondary-color); }
.gp-btn--outline { background: var(--bg-1); border-color: var(--divider-2); color: var(--txt-color-2); }

.gp-checkbox {
  width: 15px;
  height: 15px;
  cursor: pointer;
  accent-color: var(--brand-secondary-color);
  flex-shrink: 0;
}

.gp-cb-control {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
}

.gp-cb-label {
  font-size: 13px;
  color: var(--txt-color-1);
  cursor: pointer;
}

/* [interview-side:css-start] */
/* ── 목업 + 인터뷰 질문지 분할 (list와 동일) ── */
.gp-page-split {
  display: flex;
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  align-items: stretch;
}

.gp-page-split__main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.gp-page-split__main :deep(.std-edit) {
  flex: 1;
  min-height: 0;
}

.gp-page-split__side {
  width: min(360px, 38vw);
  flex-shrink: 0;
  border-left: 1px solid var(--divider-1);
  background: var(--bg-2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  overflow-y: auto;
}

.gp-side-title {
  flex-shrink: 0;
  margin: 0;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 700;
  color: var(--txt-color-1);
  border-bottom: 1px solid var(--divider-1);
  background: var(--bg-1);
}

.gp-side-list {
  flex: 1;
  margin: 0;
  padding: 10px 12px 14px 28px;
  overflow-y: auto;
  font-size: 12px;
  color: var(--txt-color-2);
  line-height: 1.55;
}

.gp-side-item {
  margin-bottom: 12px;
}

.gp-side-item::marker {
  color: var(--txt-color-4);
  font-weight: 600;
}

.gp-side-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 4px;
}

.gp-side-cat {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-1);
  color: var(--txt-color-3);
  border: 1px solid var(--divider-1);
}

.gp-side-pri {
  font-size: 10px;
  font-weight: 600;
}

.gp-side-pri--high { color: #dc2626; }
.gp-side-pri--mid { color: var(--txt-color-3); }
.gp-side-pri--low { color: var(--txt-color-4); }

.gp-side-q {
  margin: 0 0 6px;
  color: var(--txt-color-1);
  font-size: 12px;
}

.gp-side-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--divider-1);
  background: var(--bg-1);
}

.gp-side-copy-btn {
  flex-shrink: 0;
  height: 26px;
  padding: 0 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--divider-2);
  background: var(--bg-1);
  color: var(--txt-color-2);
  transition: background 0.15s, color 0.15s;
}


.gp-side-header-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

.gp-side-add-btn {
  height: 26px; padding: 0 10px; border-radius: 4px; font-size: 11px; font-weight: 600;
  cursor: pointer; border: 1px solid var(--brand-secondary-color); background: var(--bg-1);
  color: var(--brand-secondary-color); transition: background 0.15s, color 0.15s; white-space: nowrap;
}
.gp-side-add-btn:hover { background: var(--brand-secondary-color); color: #fff; }
.gp-side-add-btn--ghost { height: 32px; padding: 0 14px; font-size: 12px; border-style: dashed; }
.gp-side-custom { flex-shrink: 0; border-top: 2px dashed var(--divider-1); }
.gp-side-custom-divider { font-size: 11px; font-weight: 600; color: var(--txt-color-3); padding: 8px 14px 4px; letter-spacing: 0.03em; }
.gp-side-list--custom { padding-top: 4px; }
.gp-side-item--custom { list-style: none; padding: 10px 10px 10px 12px; border: 1px solid var(--divider-1); border-radius: 6px; background: var(--bg-1); margin-bottom: 10px; }
.gp-side-custom-q-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.gp-side-custom-q-input { flex: 1; min-width: 0; height: 30px; padding: 0 8px; border: 1px solid var(--divider-2); border-radius: 4px; font-size: 12px; font-weight: 500; color: var(--txt-color-1); background: var(--bg-2); outline: none; transition: border-color 0.15s; }
.gp-side-custom-q-input:focus { border-color: var(--brand-secondary-color); background: #fff; }
.gp-side-custom-q-input::placeholder { color: var(--txt-color-4); font-weight: 400; }
.gp-side-del-btn { flex-shrink: 0; width: 24px; height: 24px; border: none; border-radius: 4px; background: transparent; color: var(--txt-color-4); font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.15s, color 0.15s; }
.gp-side-del-btn:hover { background: #fee2e2; color: #ef4444; }
.gp-side-custom-empty { padding: 12px 14px 16px; display: flex; justify-content: center; }
.gp-side-copy-btn:hover { background: var(--bg-2); }
.gp-side-copy-btn--done { background: #f0fdf4; border-color: #bbf7d0; color: #16a34a; }

.gp-side-answer {
  display: block;
  width: 100%;
  box-sizing: border-box;
  margin-top: 4px;
  padding: 7px 9px;
  border: 1px solid var(--divider-2);
  border-radius: 5px;
  font-size: 12px;
  font-family: inherit;
  line-height: 1.5;
  color: var(--txt-color-1);
  background: var(--bg-1);
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}

.gp-side-answer:focus {
  border-color: var(--brand-secondary-color);
  background: #fff;
}


/* ── 인터뷰결과생성 영역 ── */
.gp-side-result-area {
  flex-shrink: 0; padding: 12px 14px 16px; border-top: 2px solid var(--divider-1);
  background: var(--bg-1); display: flex; flex-direction: column; gap: 8px;
}
.gp-side-result-msg { font-size: 11px; line-height: 1.5; padding: 8px 10px; border-radius: 5px; }
.gp-side-result-msg--ok  { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.gp-side-result-msg--err { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.gp-side-generate-btn {
  width: 100%; height: 36px; border-radius: 6px; font-size: 13px; font-weight: 700;
  cursor: pointer; border: 1.5px solid var(--divider-2); background: var(--bg-2);
  color: var(--txt-color-3); transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.gp-side-generate-btn--ready { border-color: var(--brand-secondary-color); background: var(--brand-secondary-color); color: #fff; }
.gp-side-generate-btn--ready:hover { opacity: 0.9; }
.gp-side-generate-btn:disabled { cursor: not-allowed; opacity: 0.6; }
.gp-side-generate-hint { margin: 0; font-size: 10px; color: var(--txt-color-4); text-align: center; }
/* ── 붙여넣기 버튼·모달 ── */
.gp-side-paste-btn {
  width: 100%; padding: 7px 10px; border: 1px dashed #94a3b8; border-radius: 6px;
  background: #f8fafc; cursor: pointer; font-size: 12px; color: #475569;
  transition: all 0.15s; text-align: center;
}
.gp-side-paste-btn:hover { border-color: #3b82f6; color: #3b82f6; background: #eff6ff; }
.gp-paste-confirmed {
  font-size: 11px; color: #16a34a; background: #f0fdf4; border: 1px solid #bbf7d0;
  border-radius: 5px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center;
}
.gp-paste-reset-btn {
  background: none; border: none; cursor: pointer; font-size: 11px; color: #9ca3af; text-decoration: underline;
}
.gp-paste-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}
.gp-paste-modal {
  background: #fff; border-radius: 12px; padding: 24px 28px 20px; width: 580px; max-width: 95vw;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2); display: flex; flex-direction: column; gap: 14px;
}
.gp-paste-modal-header { display: flex; justify-content: space-between; align-items: center; }
.gp-paste-modal-title { margin: 0; font-size: 16px; font-weight: 600; color: #111827; }
.gp-paste-modal-close {
  background: none; border: none; cursor: pointer; font-size: 18px; color: #9ca3af; line-height: 1;
  padding: 2px 6px; border-radius: 4px;
}
.gp-paste-modal-close:hover { color: #374151; background: #f3f4f6; }
.gp-paste-modal-desc { margin: 0; font-size: 13px; color: #6b7280; line-height: 1.6; }
.gp-paste-textarea {
  width: 100%; min-height: 260px; border: 1px solid #d1d5db; border-radius: 8px;
  padding: 12px 14px; font-size: 13px; resize: vertical; font-family: inherit;
  box-sizing: border-box; line-height: 1.7; color: #374151;
}
.gp-paste-textarea:focus { outline: 2px solid #3b82f6; border-color: transparent; }
.gp-paste-modal-footer { display: flex; justify-content: flex-end; gap: 8px; }
.gp-paste-cancel-btn {
  padding: 8px 18px; border: 1px solid #d1d5db; border-radius: 7px;
  background: #fff; cursor: pointer; font-size: 13px; color: #374151;
}
.gp-paste-cancel-btn:hover { background: #f9fafb; }
.gp-paste-save-btn {
  padding: 8px 20px; border: none; border-radius: 7px;
  background: #3b82f6; color: #fff; cursor: pointer; font-size: 13px; font-weight: 600;
}
.gp-paste-save-btn:disabled { background: #9ca3af; cursor: not-allowed; }
.gp-paste-save-btn:not(:disabled):hover { background: #2563eb; }
/* [interview-side:css-end] */
.gp-side-answer::placeholder {
  color: var(--txt-color-4);
  font-style: italic;
}
</style>
`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  AST Router Updater (ts-morph)
//  staticRoutes.ts 의 staticRoutes 배열에 경로 추가
// ─────────────────────────────────────────────────────────────────────────────
function addRouteToStaticRoutes(pageName: string, routePath: string): void {
  const project = new Project({ skipAddingFilesFromTsConfig: true });
  const sourceFile = project.addSourceFileAtPath(PATHS.staticRoutes);

  const routesVar = sourceFile.getVariableDeclaration('staticRoutes');
  if (!routesVar) throw new Error('staticRoutes 변수를 찾을 수 없습니다.');

  const arrayInit = routesVar.getInitializerIfKind(SyntaxKind.ArrayLiteralExpression);
  if (!arrayInit) throw new Error('staticRoutes 배열 초기화를 찾을 수 없습니다.');

  // 중복 방지
  const existing = arrayInit.getText();
  const routeName = `generated-${pageName}`;
  if (existing.includes(`'${routeName}'`) || existing.includes(`"${routeName}"`)) {
    console.log(`[generate] route '${routeName}' already exists, skipping.`);
    return;
  }

  // NotFound catch-all 앞에 삽입
  const elements  = arrayInit.getElements();
  const catchAllIdx = elements.findIndex(el => el.getText().includes("'/:pathMatch"));
  const routeCode = `{
    path: '${routePath}',
    name: '${routeName}',
    meta: { generated: true },
    component: () => import('@/pages/generated/${pageName}.vue'),
  }`;

  if (catchAllIdx >= 0) {
    arrayInit.insertElement(catchAllIdx, routeCode);
  } else {
    arrayInit.addElement(routeCode);
  }

  sourceFile.saveSync();
  console.log(`[generate] route added: ${routePath} → @/pages/generated/${pageName}.vue`);
}

// ─────────────────────────────────────────────────────────────────────────────
//  POST /api/generate
//  Page Spec JSON을 받아 Vue 목업 페이지 파일을 생성하고 라우터에 등록
// ─────────────────────────────────────────────────────────────────────────────
router.post('/', (req: Request, res: Response) => {
  const spec = req.body as PageSpec;

  /* ── 입력 검증 ── */
  if (!spec.pageName?.trim() || !spec.routePath?.trim() || !spec.pageType) {
    return res.status(400).json({
      success: false,
      message: 'pageName, routePath, pageType 은 필수 입력 항목입니다.',
    });
  }

  if (!/^[A-Za-z0-9_-]+$/.test(spec.pageName)) {
    return res.status(400).json({
      success: false,
      message: 'pageName 은 영문·숫자·하이픈·언더스코어만 허용됩니다.',
    });
  }

  /* ── detail → 미구현 ── */
  if (spec.pageType === 'detail') {
    return res.status(400).json({
      success: false,
      message: 'detail 타입은 아직 준비 중입니다.',
    });
  }

  try {
    /* ── Vue SFC 생성 ── */
    const vueCode = spec.pageType === 'form'
      ? generateFormVue(spec)
      : generateListVue(spec);
    const pagesGenDir = path.join(PATHS.srcDir, 'pages', 'generated');
    const pagePath    = path.join(pagesGenDir, `${spec.pageName}.vue`);

    ensureDir(pagesGenDir);
    fs.writeFileSync(pagePath, vueCode, 'utf-8');
    console.log(`[generate] file written: ${pagePath}`);

    /* ── 라우터 AST 업데이트 ── */
    addRouteToStaticRoutes(spec.pageName, spec.routePath);

    return res.status(201).json({
      success:   true,
      pagePath,
      routePath: spec.routePath,
    });
  } catch (err) {
    console.error('[generate] error:', err);
    return res.status(500).json({
      success: false,
      message: `생성 중 오류: ${(err as Error).message}`,
    });
  }
});

export default router;
