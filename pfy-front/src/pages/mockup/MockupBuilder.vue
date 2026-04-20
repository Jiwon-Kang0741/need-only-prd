<template>
  <div class="mb">

    <!-- ── 헤더 ── -->
    <div class="mb__header">
      <h1 class="mb__title">MockUp Builder</h1>
      <p class="mb__subtitle">화면 스펙을 정의하고 Vue 목업 페이지를 자동 생성합니다. (scaffolding 서버 port 4000 실행 필요)</p>
    </div>

    <div class="mb__body">

      <!-- ─────────────────────────────────────────────
           왼쪽: 설정 폼
      ───────────────────────────────────────────── -->
      <div class="mb__form-panel">

        <!-- 기본 정보 -->
        <section class="mb__section">
          <h2 class="mb__section-title">기본 정보</h2>

          <div class="mb__field">
            <label class="mb__label">페이지 타입</label>
            <Select
              v-model="spec.pageType"
              :options="PAGE_TYPE_OPTIONS"
              optionLabel="label"
              optionValue="value"
              style="width: 100%"
            />
          </div>

          <div class="mb__field">
            <label class="mb__label">페이지명 <span class="mb__required">*</span></label>
            <InputText v-model="spec.pageName" placeholder="예: MemberList" style="width: 100%" />
            <small class="mb__hint">생성 파일명 및 라우트 name 으로 사용됩니다.</small>
          </div>

          <div class="mb__field">
            <label class="mb__label">라우트 경로 <span class="mb__required">*</span></label>
            <InputText v-model="spec.routePath" placeholder="예: /generated/member-list" style="width: 100%" />
          </div>

          <div class="mb__field">
            <label class="mb__label">화면 제목</label>
            <InputText v-model="spec.title" placeholder="예: 회원 목록" style="width: 100%" />
          </div>

          <div v-if="spec.pageType !== 'detail'" class="mb__field">
            <label class="mb__label">화면 설명 <span class="mb__hint-inline">(선택 — AI 추천 품질 향상)</span></label>
            <InputText v-model="spec.description" placeholder="예: 시스템 사용자의 접근 이력을 조회하는 화면" style="width: 100%" />
          </div>

          <!-- AI 자동생성 -->
          <div v-if="spec.pageType !== 'detail'" class="mb__ai-bar">
            <Button
              label="AI 자동생성"
              icon="pi pi-sparkles"
              severity="secondary"
              :loading="aiGenerating"
              :disabled="!spec.title.trim()"
              @click="generateWithAI"
            />
            <span class="mb__ai-hint">화면 제목/설명 기반으로 필드를 자동 추천합니다</span>
            <span v-if="aiError" class="mb__ai-error">{{ aiError }}</span>
          </div>
        </section>

        <!-- ── List 타입 전용 ── -->
        <template v-if="spec.pageType === 'list'">

          <!-- 검색 필드 -->
          <section class="mb__section">
            <div class="mb__section-header">
              <h2 class="mb__section-title">검색 필드</h2>
              <Button label="+ 추가" size="small" severity="secondary" variant="outlined" @click="addSearchField" />
            </div>

            <template v-if="spec.searchFields.length">
              <div class="mb__grid-head mb__grid--4col">
                <span>Key <span class="mb__key-hint">(영문만)</span></span><span>레이블</span><span>타입</span><span>옵션</span><span />
              </div>
              <template v-for="(field, i) in spec.searchFields" :key="i">
                <div class="mb__grid-row mb__grid--4col">
                  <InputText
                    :model-value="field.key"
                    placeholder="key (영문)"
                    size="small"
                    style="width:100%"
                    @update:model-value="(v) => onKeyInput(field, v as string)"
                  />
                  <InputText v-model="field.label" placeholder="레이블" size="small" style="width:100%" />
                  <Select
                    v-model="field.type"
                    :options="FIELD_TYPE_OPTIONS"
                    optionLabel="label"
                    optionValue="value"
                    size="small"
                    style="width:100%"
                  />
                  <span v-if="field.type === 'select'" class="mb__type-hint mb__type-hint--muted">
                    아래에서 설정
                  </span>
                  <span v-else class="mb__type-hint">
                    <template v-if="field.type === 'daterange'">from ~ to 자동 생성</template>
                    <template v-else-if="field.type === 'checkbox'">true/false 필터</template>
                  </span>
                  <button class="mb__del-btn" title="삭제" @click="removeSearchField(i)">✕</button>
                </div>
                <!-- select 타입: 옵션 방식 선택 -->
                <div v-if="field.type === 'select'" class="mb__option-row">
                  <div class="mb__option-toggle">
                    <label class="mb__option-radio">
                      <input type="radio" :name="`sf-optMode-${i}`" value="direct" :checked="(field.optionMode ?? 'direct') === 'direct'" @change="field.optionMode = 'direct'" />
                      직접 입력
                    </label>
                    <label class="mb__option-radio">
                      <input type="radio" :name="`sf-optMode-${i}`" value="codeClass" :checked="field.optionMode === 'codeClass'" @change="field.optionMode = 'codeClass'" />
                      공통코드 그룹 참조
                    </label>
                  </div>
                  <InputText
                    v-if="(field.optionMode ?? 'direct') === 'direct'"
                    v-model="field.optionsText"
                    placeholder="v1:라벨1, v2:라벨2"
                    size="small"
                    style="width:100%"
                  />
                  <InputText
                    v-else
                    v-model="field.codeClass"
                    placeholder="공통코드 그룹 (code_class) 예) YN_TYPE"
                    size="small"
                    class="mb__codeinput"
                    style="width:100%"
                  />
                </div>
              </template>
            </template>
            <p v-else class="mb__empty">검색 필드가 없습니다.</p>
          </section>

          <!-- 테이블 컬럼 -->
          <section class="mb__section">
            <div class="mb__section-header">
              <h2 class="mb__section-title">테이블 컬럼</h2>
              <Button label="+ 추가" size="small" severity="secondary" variant="outlined" @click="addColumn" />
            </div>

            <template v-if="spec.tableColumns.length">
              <div class="mb__grid-head mb__grid--2col">
                <span>Key <span class="mb__key-hint">(영문만)</span></span><span>헤더명</span><span />
              </div>
              <div
                v-for="(col, i) in spec.tableColumns"
                :key="i"
                class="mb__grid-row mb__grid--2col"
              >
                <InputText
                  :model-value="col.key"
                  placeholder="key (영문)"
                  size="small"
                  style="width:100%"
                  @update:model-value="(v) => onKeyInput(col, v as string)"
                />
                <InputText v-model="col.label" placeholder="헤더명" size="small" style="width:100%" />
                <button class="mb__del-btn" title="삭제" @click="removeColumn(i)">✕</button>
              </div>
            </template>
            <p v-else class="mb__empty">컬럼이 없습니다.</p>
          </section>

          <!-- 버튼 액션 -->
          <section class="mb__section">
            <h2 class="mb__section-title">버튼 액션</h2>
            <div class="mb__checkboxes">
              <label
                v-for="action in ACTION_OPTIONS"
                :key="action.value"
                class="mb__checkbox-label"
              >
                <Checkbox v-model="actionFlags[action.value]" :binary="true" />
                <span>{{ action.label }}</span>
              </label>
            </div>
          </section>

          <!-- 목업 데이터 수 -->
          <section class="mb__section">
            <h2 class="mb__section-title">목업 데이터 수</h2>
            <InputNumber
              v-model="spec.mockDataCount"
              :min="1"
              :max="100"
              showButtons
              style="width: 180px"
            />
          </section>
        </template>

        <!-- ── Form 타입 전용 ── -->
        <template v-else-if="spec.pageType === 'form'">

          <!-- 폼 필드 -->
          <section class="mb__section">
            <div class="mb__section-header">
              <h2 class="mb__section-title">폼 필드</h2>
              <Button label="+ 추가" size="small" severity="secondary" variant="outlined" @click="addFormField" />
            </div>

            <template v-if="spec.formFields.length">
              <div class="mb__grid-head mb__grid--form">
                <span>Key <span class="mb__key-hint">(영문만)</span></span>
                <span>레이블</span>
                <span>타입</span>
                <span style="text-align:center">필수</span>
                <span>옵션 (select용, value:label)</span>
                <span />
              </div>
              <template v-for="(field, i) in spec.formFields" :key="i">
                <div class="mb__grid-row mb__grid--form">
                  <InputText
                    :model-value="field.key"
                    placeholder="key (영문)"
                    size="small"
                    style="width:100%"
                    @update:model-value="(v) => onKeyInput(field, v as string)"
                  />
                  <InputText v-model="field.label" placeholder="레이블" size="small" style="width:100%" />
                  <Select
                    v-model="field.type"
                    :options="FORM_FIELD_TYPE_OPTIONS"
                    optionLabel="label"
                    optionValue="value"
                    size="small"
                    style="width:100%"
                  />
                  <div style="display:flex;justify-content:center;align-items:center">
                    <Checkbox v-model="field.required" :binary="true" />
                  </div>
                  <span v-if="field.type === 'select'" class="mb__type-hint mb__type-hint--muted">
                    아래에서 설정
                  </span>
                  <span v-else class="mb__type-hint">
                    <template v-if="field.type === 'checkbox'">boolean (true/false)</template>
                  </span>
                  <button class="mb__del-btn" title="삭제" @click="removeFormField(i)">✕</button>
                </div>
                <!-- select 타입: 옵션 방식 선택 -->
                <div v-if="field.type === 'select'" class="mb__option-row">
                  <div class="mb__option-toggle">
                    <label class="mb__option-radio">
                      <input type="radio" :name="`ff-optMode-${i}`" value="direct" :checked="(field.optionMode ?? 'direct') === 'direct'" @change="field.optionMode = 'direct'" />
                      직접 입력
                    </label>
                    <label class="mb__option-radio">
                      <input type="radio" :name="`ff-optMode-${i}`" value="codeClass" :checked="field.optionMode === 'codeClass'" @change="field.optionMode = 'codeClass'" />
                      공통코드 그룹 참조
                    </label>
                  </div>
                  <InputText
                    v-if="(field.optionMode ?? 'direct') === 'direct'"
                    v-model="field.optionsText"
                    placeholder="v1:라벨1, v2:라벨2"
                    size="small"
                    style="width:100%"
                  />
                  <InputText
                    v-else
                    v-model="field.codeClass"
                    placeholder="공통코드 그룹 (code_class) 예) YN_TYPE"
                    size="small"
                    class="mb__codeinput"
                    style="width:100%"
                  />
                </div>
              </template>
            </template>
            <p v-else class="mb__empty">폼 필드가 없습니다.</p>
          </section>

        </template>

        <!-- detail → TODO -->
        <template v-else>
          <section class="mb__section mb__section--todo">
            <span class="mb__todo-badge">TODO</span>
            <p>Detail 타입은 준비 중입니다.</p>
          </section>
        </template>

        <!-- 생성 버튼 -->
        <div class="mb__cta">
          <Button
            label="페이지 생성"
            icon="pi pi-play"
            :loading="generating"
            :disabled="!canGenerate"
            @click="generate"
          />
          <small v-if="!canGenerate" class="mb__hint">pageName 과 routePath 를 입력하세요.</small>
          <small v-else class="mb__hint">클릭 시 목업 파일 생성 → 질문지(LLM) → 질문지 반영 재생성 → 인라인 UI 주석(LLM) 추가 순으로 진행됩니다.</small>
        </div>
      </div>

      <!-- ─────────────────────────────────────────────
           오른쪽: JSON / 주석 + (분할) 질문지 에디터 영역
      ───────────────────────────────────────────── -->
      <div class="mb__preview-panel">
        <div class="mb__preview-split">
          <div class="mb__preview-split-main">

            <section class="mb__section">
              <h2 class="mb__section-title">Page Spec JSON</h2>
              <pre class="mb__json">{{ specJson }}</pre>
              <div v-if="spec.mockRows.length" class="mb__mock-badge">
                <i class="pi pi-sparkles" />
                AI 생성 목업 데이터 {{ spec.mockRows.length }}건 포함 — 페이지 생성 시 자동 반영됩니다
              </div>
            </section>

            <!-- 고객용 화면 가이드 주석 (LLM — 페이지 생성 시 자동) -->
            <section class="mb__section">
              <div class="mb__section-header mb__section-header--wrap">
                <h2 class="mb__section-title">UI 인라인 주석</h2>
              </div>
              <p class="mb__interview-lead">
                <strong>페이지 생성</strong> 완료 후
                <code>RequirementPrompt/annotationPrompt.md</code> 지침에 따라 LLM이
                각 UI 요소 위에 <code>/** @id, @type, @summary … */</code> 구조화된 인라인 주석을 추가합니다.
              </p>
              <p v-if="annotationError" class="mb__ai-error mb__interview-error">{{ annotationError }}</p>
              <div v-if="annotationMarkdown" class="mb__annotation-ok">{{ annotationMarkdown }}</div>
              <p v-else-if="!generating" class="mb__empty mb__empty--muted">아직 생성된 주석이 없습니다. 페이지 생성을 실행하세요.</p>
            </section>

            <!-- 생성 성공 -->
            <section v-if="result" class="mb__section">
              <h2 class="mb__section-title">생성 결과</h2>
              <div class="mb__result mb__result--success">
                <div class="mb__result-status">
                  <i class="pi pi-check-circle" />
                  페이지 생성 완료
                </div>
                <div class="mb__result-row">
                  <span class="mb__result-label">파일</span>
                  <code class="mb__result-code">{{ result.pagePath }}</code>
                </div>
                <div class="mb__result-row">
                  <span class="mb__result-label">URL</span>
                  <code class="mb__result-code">{{ result.previewUrl }}</code>
                </div>
                <div class="mb__result-actions">
                  <a
                    :href="result.previewUrl"
                    target="_blank"
                    class="mb__preview-btn"
                  >
                    <i class="pi pi-external-link" />
                    새 탭에서 미리보기 열기
                  </a>
                  <button class="mb__copy-btn" @click="copyUrl(result.previewUrl)">
                    <i :class="copied ? 'pi pi-check' : 'pi pi-copy'" />
                    {{ copied ? '복사됨!' : 'URL 복사' }}
                  </button>
                </div>
              </div>
            </section>

            <!-- 에러 -->
            <section v-if="errorMsg" class="mb__section">
              <div class="mb__result mb__result--error">
                <i class="pi pi-times-circle" />
                <span>{{ errorMsg }}</span>
              </div>
            </section>

          </div>

          <div class="mb__preview-split-side">
            <section class="mb__section mb__section--sticky-side">
              <h2 class="mb__section-title">요구사항 인터뷰 질문지</h2>
              <p class="mb__interview-lead">
                <strong>페이지 생성</strong> 시 <strong>① 질문지(LLM)</strong> → <strong>② UI 주석(LLM)</strong> 순으로 진행되며,
                아래 내용은 생성된 목업 화면 <strong>오른쪽 패널</strong>과 동일합니다.
                화면 제목이 비어 있으면 페이지명을 질문 생성에 사용합니다.
              </p>

              <div v-if="generating && interviewStep" class="mb__interview-steps">
                <div :class="['mb__interview-step', interviewStep === 'questioning' ? 'mb__interview-step--active' : interviewStep === 'annotating' ? 'mb__interview-step--done' : '']">
                  <span class="mb__interview-step-no">1</span>
                  <span class="mb__interview-step-label">질문지 생성</span>
                  <span v-if="interviewStep === 'questioning'" class="mb__interview-step-badge mb__interview-step-badge--running">진행 중</span>
                  <span v-else-if="interviewStep === 'annotating'" class="mb__interview-step-badge mb__interview-step-badge--done">완료</span>
                </div>
                <div class="mb__interview-step-arrow">→</div>
                <div :class="['mb__interview-step', interviewStep === 'annotating' ? 'mb__interview-step--active' : '']">
                  <span class="mb__interview-step-no">2</span>
                  <span class="mb__interview-step-label">UI 주석 생성</span>
                  <span v-if="interviewStep === 'annotating'" class="mb__interview-step-badge mb__interview-step-badge--running">진행 중</span>
                </div>
              </div>

              <p v-if="interviewError" class="mb__ai-error mb__interview-error">{{ interviewError }}</p>

              <div v-if="interviewQuestions.length" class="mb__interview-source-bar">
                <span v-if="interviewSource === 'annotation'" class="mb__interview-source mb__interview-source--annotation">
                  주석 기반 생성
                </span>
                <span v-else-if="interviewSource === 'spec'" class="mb__interview-source mb__interview-source--spec">
                  스펙 JSON 기반 생성
                </span>
              </div>

              <textarea
                class="mb__interview-editor"
                readonly
                rows="24"
                :value="interviewQuestionsPlain"
                placeholder="페이지 생성 후 자동으로 채워집니다."
              />
            </section>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed } from 'vue';
import { Select } from '@/components/common/select';
import { InputText } from '@/components/common/inputText';
import { InputNumber } from '@/components/common/inputNumber';
import { Button } from '@/components/common/button';
import Checkbox from 'primevue/checkbox';

// ── Types ─────────────────────────────────────────────────────────────────
type PageType = 'list' | 'detail' | 'form';
type FieldType = 'text' | 'number' | 'date' | 'daterange' | 'select' | 'checkbox';
type FormFieldType = 'text' | 'number' | 'date' | 'select' | 'textarea' | 'checkbox';

interface SearchField {
  key: string;
  label: string;
  type: FieldType;
  optionsText: string;
  optionMode: 'direct' | 'codeClass';
  codeClass: string;
}

interface TableColumn {
  key: string;
  label: string;
}

interface FormField {
  key: string;
  label: string;
  type: FormFieldType;
  required: boolean;
  optionsText: string;
  optionMode: 'direct' | 'codeClass';
  codeClass: string;
}

interface PageSpec {
  pageType: PageType;
  pageName: string;
  routePath: string;
  title: string;
  description: string;
  searchFields: SearchField[];
  tableColumns: TableColumn[];
  formFields: FormField[];
  mockDataCount: number;
  mockRows: Record<string, string>[];
}

interface GenerateResult {
  success: boolean;
  pagePath: string;
  routePath: string;
  previewUrl: string; // 프론트엔드에서 조립
}

// ── Constants ──────────────────────────────────────────────────────────────
const PAGE_TYPE_OPTIONS = [
  { label: 'List (목록)', value: 'list' },
  { label: 'Detail (상세)', value: 'detail' },
  { label: 'Form (입력/수정)', value: 'form' },
] as const;

const FIELD_TYPE_OPTIONS = [
  { label: '텍스트', value: 'text' },
  { label: '숫자', value: 'number' },
  { label: '날짜', value: 'date' },
  { label: '날짜 범위(from~to)', value: 'daterange' },
  { label: '선택(select)', value: 'select' },
  { label: '체크박스', value: 'checkbox' },
] as const;

const FORM_FIELD_TYPE_OPTIONS = [
  { label: '텍스트', value: 'text' },
  { label: '숫자', value: 'number' },
  { label: '날짜', value: 'date' },
  { label: '선택(select)', value: 'select' },
  { label: '여러줄(textarea)', value: 'textarea' },
  { label: '체크박스', value: 'checkbox' },
] as const;

const ACTION_OPTIONS = [
  { label: '등록 (create)', value: 'create' },
  { label: '엑셀 다운로드 (excel)', value: 'excel' },
  { label: '상세 (detail)', value: 'detail' },
  { label: '삭제 (delete)', value: 'delete' },
] as const;

const SCAFFOLDING_API       = 'http://localhost:4000/api/generate';
const AI_INTERVIEW_API      = 'http://localhost:4000/api/ai-interview-questions';
const AI_ANNOTATE_API       = 'http://localhost:4000/api/ai-annotate';

// ── State ──────────────────────────────────────────────────────────────────
const spec = reactive<PageSpec>({
  pageType: 'list',
  pageName: '',
  routePath: '',
  title: '',
  description: '',
  searchFields: [],
  tableColumns: [],
  formFields: [],
  mockDataCount: 10,
  mockRows: [],
});

/** 액션 체크박스 (boolean 맵 → generate 시 string[] 로 변환) */
const actionFlags = reactive<Record<string, boolean>>({
  create: false,
  excel: false,
  detail: false,
  delete: false,
});

const generating   = ref(false);
const result       = ref<GenerateResult | null>(null);
const errorMsg     = ref('');
const copied       = ref(false);
const aiGenerating = ref(false);
const aiError      = ref('');

interface InterviewQuestionItem {
  no: number;
  category: string;
  question: string;
  priority: 'high' | 'medium' | 'low';
}
const interviewError     = ref('');
const interviewQuestions = ref<InterviewQuestionItem[]>([]);
const interviewSource    = ref<'annotation' | 'spec' | ''>('');
const interviewStep      = ref<'' | 'annotating' | 'questioning'>('');

const annotationError     = ref('');
const annotationMarkdown  = ref('');
const annotationCopied    = ref(false);

// ── Computed ───────────────────────────────────────────────────────────────
/** 요청 payload (JSON 문자열) */
const specJson = computed(() => {
  const actions = ACTION_OPTIONS.map(a => a.value).filter(v => actionFlags[v]);

  const searchFields = spec.searchFields.map(f => {
    const base = { key: f.key, label: f.label, type: f.type } as Record<string, unknown>;
    if (f.type === 'select') {
      if (f.optionMode === 'codeClass' && f.codeClass.trim()) {
        base.optionMode = 'codeClass';
        base.codeClass  = f.codeClass.trim();
      } else if (f.optionsText.trim()) {
        base.options = f.optionsText.split(',').map(segment => {
          const [rawVal, rawLabel] = segment.trim().split(':');
          return {
            value: rawVal?.trim() ?? segment.trim(),
            label: rawLabel?.trim() ?? rawVal?.trim() ?? segment.trim(),
          };
        });
      }
    }
    return base;
  });

  const formFields = spec.formFields.map(f => {
    const base = { key: f.key, label: f.label, type: f.type, required: f.required } as Record<string, unknown>;
    if (f.type === 'select') {
      if (f.optionMode === 'codeClass' && f.codeClass.trim()) {
        base.optionMode = 'codeClass';
        base.codeClass  = f.codeClass.trim();
      } else if (f.optionsText.trim()) {
        base.options = f.optionsText.split(',').map(segment => {
          const [rawVal, rawLabel] = segment.trim().split(':');
          return {
            value: rawVal?.trim() ?? segment.trim(),
            label: rawLabel?.trim() ?? rawVal?.trim() ?? segment.trim(),
          };
        });
      }
    }
    return base;
  });

  const base = {
    pageType:    spec.pageType,
    pageName:    spec.pageName,
    routePath:   spec.routePath,
    title:       spec.title,
    description: spec.description,
    searchFields,
    tableColumns: spec.tableColumns,
    formFields,
    actions,
    mockDataCount: spec.mockDataCount,
    mockRows: spec.mockRows,
  };

  // 미리보기용: mockRows가 있으면 건수 요약으로 표시
  const preview = { ...base, mockRows: spec.mockRows.length ? `[AI 생성 ${spec.mockRows.length}건 — 전송 시 실제 데이터 포함]` : [] };
  return JSON.stringify(preview, null, 2);
});

const canGenerate = computed(
  () => !!spec.pageName.trim() && !!spec.routePath.trim(),
);

function interviewPriorityLabel(p: string): string {
  const x = (p ?? 'medium').toLowerCase();
  if (x === 'high') return '높음';
  if (x === 'low') return '낮음';
  return '보통';
}

/** 빌더 우측 에디터용 질문지 텍스트 (생성 목업 오른쪽 패널과 동일 구성) */
const interviewQuestionsPlain = computed(() => {
  if (!interviewQuestions.value.length) return '';
  return interviewQuestions.value
    .map(
      (q, i) =>
        `${i + 1}. [${q.category || '—'}] (${interviewPriorityLabel(q.priority)}) ${q.question}`,
    )
    .join('\n\n');
});

/** 페이지 생성 / LLM API 공통 payload */
function buildGeneratePayload(extras?: {
  annotationMarkdown?: string;
  interviewQuestions?: InterviewQuestionItem[];
}): Record<string, unknown> {
  const actions = ACTION_OPTIONS.map(a => a.value).filter(v => actionFlags[v]);
  const searchFields = spec.searchFields.map(f => {
    const base = { key: f.key, label: f.label, type: f.type } as Record<string, unknown>;
    if (f.type === 'select') {
      if (f.optionMode === 'codeClass' && f.codeClass.trim()) {
        base.optionMode = 'codeClass';
        base.codeClass  = f.codeClass.trim();
      } else if (f.optionsText.trim()) {
        base.options = f.optionsText.split(',').map(s => {
          const [rv, rl] = s.trim().split(':');
          return { value: rv?.trim() ?? s.trim(), label: rl?.trim() ?? rv?.trim() ?? s.trim() };
        });
      }
    }
    return base;
  });
  const formFields = spec.formFields.map(f => {
    const base = { key: f.key, label: f.label, type: f.type, required: f.required } as Record<string, unknown>;
    if (f.type === 'select') {
      if (f.optionMode === 'codeClass' && f.codeClass.trim()) {
        base.optionMode = 'codeClass';
        base.codeClass  = f.codeClass.trim();
      } else if (f.optionsText.trim()) {
        base.options = f.optionsText.split(',').map(s => {
          const [rv, rl] = s.trim().split(':');
          return { value: rv?.trim() ?? s.trim(), label: rl?.trim() ?? rv?.trim() ?? s.trim() };
        });
      }
    }
    return base;
  });
  const payload: Record<string, unknown> = {
    pageType:      spec.pageType,
    pageName:      spec.pageName,
    routePath:     spec.routePath,
    title:         spec.title,
    description:   spec.description,
    searchFields,
    tableColumns:  spec.tableColumns,
    formFields,
    actions,
    mockDataCount: spec.mockDataCount,
    mockRows:      spec.mockRows,
  };
  if (extras?.annotationMarkdown?.trim()) {
    payload.annotationMarkdown = extras.annotationMarkdown.trim();
  }
  if (extras?.interviewQuestions?.length) {
    payload.interviewQuestions = extras.interviewQuestions;
  }
  return payload;
}

// ── Methods ────────────────────────────────────────────────────────────────
/** key 입력을 유효한 JS 식별자로 즉시 정규화 */
function sanitizeKeyInput(raw: string): string {
  return raw
    .replace(/\s+/g, '_')
    .replace(/[^a-zA-Z0-9_$]/g, '');
}

function onKeyInput(obj: { key: string }, val: string) {
  obj.key = sanitizeKeyInput(val);
}

function addSearchField() {
  spec.searchFields.push({ key: '', label: '', type: 'text', optionsText: '', optionMode: 'direct', codeClass: '' });
}

function removeSearchField(index: number) {
  spec.searchFields.splice(index, 1);
}

function addColumn() {
  spec.tableColumns.push({ key: '', label: '' });
  spec.mockRows = []; // 컬럼 변경 시 AI 생성 데이터 초기화
}

function removeColumn(index: number) {
  spec.tableColumns.splice(index, 1);
  spec.mockRows = [];
}

function addFormField() {
  spec.formFields.push({ key: '', label: '', type: 'text', required: false, optionsText: '', optionMode: 'direct', codeClass: '' });
}

function removeFormField(index: number) {
  spec.formFields.splice(index, 1);
}

async function copyUrl(url: string) {
  try {
    await navigator.clipboard.writeText(url);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 2000);
  } catch {
    // fallback
    const el = document.createElement('textarea');
    el.value = url;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 2000);
  }
}

async function generateWithAI() {
  aiError.value = '';
  aiGenerating.value = true;

  try {
    const res = await fetch('http://localhost:4000/api/ai-generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pageType:    spec.pageType,
        title:       spec.title,
        description: spec.description,
      }),
    });

    const data = await res.json();

    if (!data.success) {
      aiError.value = data.message ?? 'AI 생성 실패';
      return;
    }

    if (spec.pageType === 'list') {
      if (Array.isArray(data.searchFields)) {
        spec.searchFields = (data.searchFields as (SearchField & { optionsText?: string })[]).map(f => ({
          key:         f.key ?? '',
          label:       f.label ?? '',
          type:        (f.type as FieldType) ?? 'text',
          optionsText: f.type === 'select' ? (f.optionsText ?? '') : '',
          optionMode:  'direct' as const,
          codeClass:   '',
        }));
      }
      if (Array.isArray(data.tableColumns)) {
        spec.tableColumns = (data.tableColumns as TableColumn[]).map(c => ({
          key:   c.key ?? '',
          label: c.label ?? '',
        }));
      }
      // AI 생성 목업 데이터 저장
      if (Array.isArray(data.mockRows)) {
        spec.mockRows = data.mockRows as Record<string, string>[];
      } else {
        spec.mockRows = [];
      }
    } else if (spec.pageType === 'form') {
      if (Array.isArray(data.formFields)) {
        spec.formFields = (data.formFields as (FormField & { optionsText?: string })[]).map(f => ({
          key:         f.key ?? '',
          label:       f.label ?? '',
          type:        (f.type as FormFieldType) ?? 'text',
          required:    !!f.required,
          optionsText: f.type === 'select' ? (f.optionsText ?? '') : '',
          optionMode:  'direct' as const,
          codeClass:   '',
        }));
      }
    }
  } catch (e) {
    aiError.value = `요청 실패: ${(e as Error).message}. scaffolding 서버(port 4000)가 실행 중인지 확인하세요.`;
  } finally {
    aiGenerating.value = false;
  }
}

async function copyAnnotationMarkdown() {
  try {
    await navigator.clipboard.writeText(annotationMarkdown.value);
    annotationCopied.value = true;
    setTimeout(() => { annotationCopied.value = false; }, 2000);
  } catch {
    const el = document.createElement('textarea');
    el.value = annotationMarkdown.value;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    annotationCopied.value = true;
    setTimeout(() => { annotationCopied.value = false; }, 2000);
  }
}

async function generate() {
  result.value = null;
  errorMsg.value = '';
  interviewError.value = '';
  annotationError.value = '';
  interviewQuestions.value = [];
  interviewSource.value = '';
  annotationMarkdown.value = '';
  interviewStep.value = '';
  generating.value = true;

  const titleForAi = spec.title.trim() || spec.pageName.trim();
  let annMd = '';
  let questions: InterviewQuestionItem[] = [];
  let firstRoutePath = '';
  let firstPagePath = '';

  try {
    /* ── Step 1: 기본 Vue 파일 생성 ── */
    const res1 = await fetch(SCAFFOLDING_API, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(buildGeneratePayload()),
    });
    const data1 = await res1.json() as GenerateResult & { success?: boolean; message?: string };

    if (!data1.success) {
      errorMsg.value = data1.message ?? '생성에 실패했습니다.';
      return;
    }

    firstRoutePath = data1.routePath;
    firstPagePath = data1.pagePath;

    /* ── Step 2: 인터뷰 질문지 생성 ── */
    interviewStep.value = 'questioning';
    try {
      const invRes = await fetch(AI_INTERVIEW_API, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          ...buildGeneratePayload(),
          title: titleForAi,
        }),
      });
      const invData = await invRes.json() as {
        success?: boolean;
        message?: string;
        questions?: InterviewQuestionItem[];
        source?: string;
      };
      if (!invData.success) {
        interviewError.value = invData.message ?? '질문지 생성에 실패했습니다.';
        questions = [];
        interviewQuestions.value = [];
      } else {
        questions = Array.isArray(invData.questions) ? invData.questions : [];
        interviewQuestions.value = questions;
        interviewSource.value = invData.source === 'annotation' ? 'annotation' : 'spec';
      }
    } catch (e) {
      interviewError.value = `질문지 요청 실패: ${(e as Error).message}`;
      interviewQuestions.value = [];
      questions = [];
    }

    /* ── Step 3: 질문지 포함 Vue 파일 재생성 ── */
    const res2 = await fetch(SCAFFOLDING_API, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(
        buildGeneratePayload({
          interviewQuestions: questions.length ? questions : undefined,
        }),
      ),
    });
    const data2 = await res2.json() as GenerateResult & { success?: boolean; message?: string };

    if (!data2.success) {
      errorMsg.value = data2.message ?? '질문지 반영 단계에서 저장에 실패했습니다.';
      result.value = {
        success:     true,
        pagePath:    firstPagePath,
        routePath:   firstRoutePath,
        previewUrl:  `${window.location.origin}${firstRoutePath}`,
      };
      return;
    }

    /* ── Step 4: 최종 파일에 인라인 UI 주석 추가 ── */
    interviewStep.value = 'annotating';
    try {
      const annRes = await fetch(AI_ANNOTATE_API, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ pageName: spec.pageName.trim() }),
      });
      const annData = await annRes.json() as { success?: boolean; message?: string; annotationCount?: number };
      if (annData.success) {
        const cnt = annData.annotationCount ?? 0;
        annotationMarkdown.value = `✓ ${cnt}개의 UI 요소에 구조화된 주석(@id, @type, @summary …)이 추가되었습니다.`;
      } else {
        annotationError.value = annData.message ?? 'UI 주석 생성에 실패했습니다.';
      }
    } catch (e) {
      annotationError.value = `UI 주석 요청 실패: ${(e as Error).message}`;
    }

    interviewStep.value = '';

    result.value = {
      ...data2,
      previewUrl: `${window.location.origin}${data2.routePath}`,
    } as GenerateResult;

    // need-only-prd 통합: 부모 React에 페이지 생성 완료 알림 → iframe 자동 전환
    try {
      window.parent?.postMessage({
        type: 'pfy-page-generated',
        routePath: data2.routePath,
        previewUrl: `${window.location.origin}${data2.routePath}`,
        pageName: spec.pageName,
      }, '*');
    } catch { /* ignore postMessage errors */ }
  } catch (e) {
    errorMsg.value = `요청 실패: ${(e as Error).message}. scaffolding 서버(port 4000)가 실행 중인지 확인하세요.`;
  } finally {
    generating.value = false;
    interviewStep.value = '';
  }
}
</script>

<style scoped lang="scss">
.mb {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-1);
  overflow: hidden;

  // ── 헤더 ──
  &__header {
    flex-shrink: 0;
    padding: 20px 28px 16px;
    border-bottom: 1px solid var(--divider-1);
    background: var(--bg-1);
  }

  &__title {
    font-size: 20px;
    font-weight: 700;
    color: var(--txt-color-1);
    margin: 0 0 4px;
  }

  &__subtitle {
    font-size: 12px;
    color: var(--txt-color-3);
    margin: 0;
  }

  // ── 바디 (2열 레이아웃) ──
  &__body {
    flex: 1;
    min-height: 0;
    display: flex;
    overflow: hidden;
  }

  // ── 왼쪽 폼 패널 ──
  &__form-panel {
    width: 520px;
    flex-shrink: 0;
    overflow-y: auto;
    padding: 20px 24px 32px;
    border-right: 1px solid var(--divider-1);
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  // ── 오른쪽 미리보기 패널 ──
  &__preview-panel {
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    padding: 20px 24px 32px;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  &__preview-split {
    display: flex;
    flex: 1;
    min-height: 0;
    gap: 20px;
    align-items: stretch;
  }

  &__preview-split-main {
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
    padding-right: 4px;
  }

  &__preview-split-side {
    width: 340px;
    flex-shrink: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--divider-1);
    border-radius: 8px;
    background: var(--bg-2);
    overflow: hidden;
  }

  &__section--sticky-side {
    margin-bottom: 0;
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 16px 16px 14px;
    overflow: hidden;
  }

  &__interview-editor {
    flex: 1;
    min-height: 200px;
    width: 100%;
    box-sizing: border-box;
    margin-top: 8px;
    padding: 10px 12px;
    border: 1px solid var(--divider-2);
    border-radius: 6px;
    font-size: 12px;
    font-family: 'Consolas', 'Monaco', 'Malgun Gothic', sans-serif;
    line-height: 1.55;
    color: var(--txt-color-1);
    background: var(--bg-1);
    resize: none;
    outline: none;
  }

  &__interview-editor:focus {
    border-color: var(--brand-secondary-color);
  }

  &__empty--muted {
    text-align: left;
    color: var(--txt-color-3);
    padding: 8px 0 0;
  }

  // ── 섹션 ──
  &__section {
    margin-bottom: 24px;

    &--todo {
      background: var(--bg-2);
      border-radius: 8px;
      padding: 20px;
      text-align: center;
      color: var(--txt-color-3);
      font-size: 13px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }
  }

  &__section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;

    &--wrap {
      flex-wrap: wrap;
      gap: 10px;
      align-items: flex-start;
    }
  }

  &__interview-lead {
    font-size: 12px;
    color: var(--txt-color-3);
    line-height: 1.6;
    margin: 0 0 12px;
  }

  &__interview-source-hint {
    font-size: 11px;
    color: var(--txt-color-3);
    opacity: 0.7;
  }

  &__interview-steps {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 0 16px;
    padding: 12px 16px;
    background: var(--bg-2);
    border-radius: 8px;
    border: 1px solid var(--border-color);
  }

  &__interview-step {
    display: flex;
    align-items: center;
    gap: 6px;
    opacity: 0.45;
    transition: opacity 0.2s;

    &--active {
      opacity: 1;
    }

    &--done {
      opacity: 0.7;
    }
  }

  &__interview-step-no {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--brand-secondary-color, #6366f1);
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
  }

  &__interview-step-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--txt-color-1);
  }

  &__interview-step-badge {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 10px;
    font-weight: 600;

    &--running {
      color: #fff;
      background: var(--brand-secondary-color, #6366f1);
      animation: pulse 1.2s ease-in-out infinite;
    }

    &--done {
      color: var(--txt-color-2);
      background: var(--bg-3, #e5e7eb);
    }
  }

  &__interview-step-arrow {
    font-size: 14px;
    color: var(--txt-color-3);
    flex-shrink: 0;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.5; }
  }

  &__interview-source-bar {
    margin-bottom: 10px;
  }

  &__interview-source {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;

    &--annotation {
      color: #fff;
      background: var(--brand-secondary-color, #6366f1);
    }

    &--spec {
      color: var(--txt-color-2);
      background: var(--bg-2);
      border: 1px solid var(--border-color);
    }
  }

  &__interview-error {
    margin-bottom: 8px;
  }

  &__interview-list {
    margin: 0;
    padding-left: 20px;
    font-size: 13px;
    color: var(--txt-color-1);
    line-height: 1.5;
  }

  &__interview-item {
    margin-bottom: 14px;
    padding-left: 4px;
  }

  &__interview-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
  }

  &__interview-cat {
    display: inline-block;
    font-size: 10px;
    font-weight: 600;
    color: var(--brand-secondary-color);
    background: var(--bg-2);
    padding: 2px 8px;
    border-radius: 4px;
  }

  &__interview-priority {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;

    &--high {
      color: #fff;
      background: #e53e3e;
    }

    &--medium {
      color: #fff;
      background: #d97706;
    }

    &--low {
      color: #fff;
      background: #6b7280;
    }
  }

  &__interview-q {
    margin: 0;
    color: var(--txt-color-1);
  }

  &__annotation-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  &__annotation-pre {
    margin: 0;
    padding: 14px 16px;
    background: var(--bg-2);
    border: 1px solid var(--divider-1);
    border-radius: 8px;
    font-size: 12px;
    font-family: 'Consolas', 'Malgun Gothic', 'Apple SD Gothic Neo', monospace;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 480px;
    overflow-y: auto;
    color: var(--txt-color-1);
  }

  &__annotation-ok {
    margin: 0;
    padding: 12px 16px;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 8px;
    font-size: 13px;
    color: #16a34a;
    font-weight: 500;
    line-height: 1.5;
  }

  &__section-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--txt-color-2);
    margin: 0 0 10px;
    padding-bottom: 6px;
    border-bottom: 2px solid var(--divider-2);

    .mb__section-header & {
      margin-bottom: 0;
      border-bottom: none;
      padding-bottom: 0;
    }
  }

  // ── 개별 필드 ──
  &__field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 12px;
  }

  &__label {
    font-size: 12px;
    font-weight: 500;
    color: var(--txt-color-3);
  }

  &__required {
    color: var(--error-color);
    margin-left: 2px;
  }

  &__hint {
    font-size: 11px;
    color: var(--txt-color-4);
  }

  // ── 동적 리스트 그리드 ──
  &__grid-head {
    display: grid;
    gap: 6px;
    font-size: 11px;
    font-weight: 500;
    color: var(--txt-color-4);
    padding: 0 2px 4px;

    &.mb__grid--4col {
      grid-template-columns: 1fr 1fr 110px 1fr 28px;
    }

    &.mb__grid--2col {
      grid-template-columns: 1fr 1fr 28px;
    }

    &.mb__grid--form {
      grid-template-columns: 1fr 1fr 120px 40px 1fr 28px;
    }
  }

  &__grid-row {
    display: grid;
    gap: 6px;
    align-items: center;
    margin-bottom: 6px;

    &.mb__grid--4col {
      grid-template-columns: 1fr 1fr 110px 1fr 28px;
    }

    &.mb__grid--2col {
      grid-template-columns: 1fr 1fr 28px;
    }

    &.mb__grid--form {
      grid-template-columns: 1fr 1fr 120px 40px 1fr 28px;
    }
  }

  &__key-hint {
    font-size: 10px;
    color: var(--txt-color-4);
    font-weight: 400;
  }

  &__type-hint {
    font-size: 11px;
    color: var(--txt-color-4);
    font-style: italic;
    display: flex;
    align-items: center;

    &--muted {
      color: var(--txt-color-4);
      font-style: normal;
      font-size: 10px;
    }
  }

  // ── 옵션 방식 선택 행 ──
  &__option-row {
    grid-column: 1 / -1;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 10px;
    margin-bottom: 6px;
    background: var(--bg-2);
    border-radius: 6px;
    border: 1px solid var(--divider-1);
  }

  &__option-toggle {
    display: flex;
    gap: 16px;
    align-items: center;
  }

  &__option-radio {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: var(--txt-color-2);
    cursor: pointer;
    user-select: none;

    input[type='radio'] {
      accent-color: var(--brand-secondary-color, #6366f1);
      cursor: pointer;
    }
  }

  &__codeinput {
    :deep(input) {
      font-family: 'Consolas', 'Monaco', monospace;
      color: #4f46e5;
      background: #eef2ff;
      border-color: #c7d2fe;

      &::placeholder {
        color: #a5b4fc;
        font-style: italic;
      }
    }
  }

  &__del-btn {
    width: 28px;
    height: 28px;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: var(--txt-color-4);
    font-size: 12px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s, color 0.15s;
    flex-shrink: 0;

    &:hover {
      background: #fee2e2;
      color: #ef4444;
    }
  }

  &__empty {
    font-size: 12px;
    color: var(--txt-color-4);
    text-align: center;
    padding: 12px 0;
    margin: 0;
  }

  // ── 체크박스 ──
  &__checkboxes {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  &__checkbox-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--txt-color-1);
    cursor: pointer;
    user-select: none;
  }

  // ── AI 자동생성 바 ──
  &__ai-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    margin-top: 4px;
    flex-wrap: wrap;
  }

  &__ai-hint {
    font-size: 12px;
    color: #3b82f6;
  }

  &__ai-error {
    font-size: 12px;
    color: var(--error-color);
    width: 100%;
  }

  &__hint-inline {
    font-size: 11px;
    color: var(--txt-color-4);
    font-weight: 400;
  }

  // ── 생성 버튼 영역 ──
  &__cta {
    padding-top: 12px;
    border-top: 1px solid var(--divider-1);
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;

    .mb__hint {
      flex: 1 1 100%;
      margin: 0;
    }
  }

  // ── AI 목업 데이터 뱃지 ──
  &__mock-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    padding: 7px 12px;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 6px;
    font-size: 12px;
    color: #16a34a;
    font-weight: 500;

    .pi {
      font-size: 13px;
    }
  }

  // ── JSON 미리보기 ──
  &__json {
    background: var(--bg-2);
    border: 1px solid var(--divider-1);
    border-radius: 6px;
    padding: 14px 16px;
    font-size: 12px;
    font-family: 'Consolas', 'Monaco', monospace;
    color: var(--txt-color-2);
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 420px;
    overflow-y: auto;
    margin: 0;
    line-height: 1.6;
  }

  // ── 결과 박스 ──
  &__result {
    border-radius: 8px;
    padding: 16px;
    font-size: 13px;

    &--success {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
    }

    &--error {
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #dc2626;
      display: flex;
      align-items: flex-start;
      gap: 8px;

      .pi {
        font-size: 16px;
        flex-shrink: 0;
        margin-top: 1px;
      }
    }
  }

  &__result-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    color: #16a34a;
    margin-bottom: 12px;

    .pi {
      font-size: 16px;
    }
  }

  &__result-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 8px;
    font-size: 13px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  &__result-label {
    flex-shrink: 0;
    width: 56px;
    font-weight: 500;
    color: var(--txt-color-3);
    padding-top: 2px;
  }

  &__result-code {
    background: var(--bg-3);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 12px;
    color: var(--txt-color-2);
    word-break: break-all;
    line-height: 1.6;
  }

  &__result-link {
    color: var(--brand-secondary-color);
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    word-break: break-all;
    font-size: 13px;

    &:hover {
      text-decoration: underline;
    }

    .pi {
      font-size: 11px;
      flex-shrink: 0;
    }
  }

  // ── 미리보기/복사 버튼 ──
  &__result-actions {
    display: flex;
    gap: 8px;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #bbf7d0;
  }

  &__preview-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 36px;
    padding: 0 16px;
    background: #16a34a;
    color: #fff;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    transition: background 0.15s;

    &:hover {
      background: #15803d;
    }

    .pi {
      font-size: 13px;
    }
  }

  &__copy-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 36px;
    padding: 0 14px;
    background: #fff;
    color: #16a34a;
    border: 1px solid #86efac;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;

    &:hover {
      background: #f0fdf4;
    }

    .pi {
      font-size: 13px;
    }
  }

  // ── TODO 배지 ──
  &__todo-badge {
    display: inline-block;
    background: #f59e0b;
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
  }
}
</style>
