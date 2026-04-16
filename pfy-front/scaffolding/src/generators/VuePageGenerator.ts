import type { FieldDef, FieldType, ScaffoldRequest, TabDef } from '../types';
import { generateMockAssets, generateFilterLogic } from './MockDataGenerator';

// ─────────────────────────────────────────────────────────────────────────────
//  Import 수집 헬퍼
// ─────────────────────────────────────────────────────────────────────────────

interface ImportNeeds {
  Select: boolean;
  InputText: boolean;
  InputNumber: boolean;
  RangeDatePicker: boolean;
  SingleDatePicker: boolean;
  Textarea: boolean;
  DotStatusText: boolean;
}

function collectImportNeeds(fields: FieldDef[]): ImportNeeds {
  const n: ImportNeeds = {
    Select: false,
    InputText: false,
    InputNumber: false,
    RangeDatePicker: false,
    SingleDatePicker: false,
    Textarea: false,
    DotStatusText: false,
  };

  for (const f of fields) {
    if (f.searchable || f.editable) {
      if (f.type === 'select' || f.type === 'radio')  n.Select        = true;
      if (f.type === 'text')                           n.InputText     = true;
      if (f.type === 'number')                         n.InputNumber   = true;
      if (f.type === 'daterange')                      n.RangeDatePicker = true;
      if (f.type === 'date')                           n.SingleDatePicker = true;
      if (f.type === 'textarea')                       n.Textarea      = true;
    }
    if ((f.listable || f.detailable) && f.type === 'badge') {
      n.DotStatusText = true;
    }
  }
  return n;
}

function buildImports(needs: ImportNeeds, pageType: string): string {
  const lines: string[] = [
    `import { ref, reactive, computed } from 'vue';`,
  ];

  // 템플릿 컴포넌트
  switch (pageType) {
    case 'list-detail':
      lines.push(`import { StandardListTemplate, StandardDetailTemplate } from '@/components/templates';`);
      break;
    case 'list':
      lines.push(`import { StandardListTemplate } from '@/components/templates';`);
      break;
    case 'edit':
      lines.push(`import { StandardEditTemplate } from '@/components/templates';`);
      break;
    case 'tab-detail':
      lines.push(`import { StandardTabTemplate } from '@/components/templates';`);
      lines.push(`import type { TabItem } from '@/components/templates';`);
      break;
  }

  // ContentHeader (index.ts 없음 — 직접 경로 import)
  lines.push(`import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue';`);

  // 페이지 유형별 공통 컴포넌트
  if (pageType === 'list' || pageType === 'list-detail') {
    lines.push(`import { SearchForm, SearchFormRow, SearchFormLabel, SearchFormField, SearchFormContent } from '@/components/common/searchForm';`);
    lines.push(`import { DataTable } from '@/components/common/dataTable2';`);
    lines.push(`import Paginator from '@/components/common/paginator/Paginator.vue';`);
    lines.push(`import Column from 'primevue/column';`);
  }

  if (pageType === 'edit' || pageType === 'list-detail' || pageType === 'tab-detail') {
    lines.push(`import { Button } from '@/components/common/button';`);
  } else {
    lines.push(`import { Button } from '@/components/common/button';`);
  }

  // 필드 타입별 컴포넌트
  if (needs.Select)          lines.push(`import { Select } from '@/components/common/select';`);
  if (needs.InputText)       lines.push(`import { InputText } from '@/components/common/inputText';`);
  if (needs.InputNumber)     lines.push(`import { InputNumber } from '@/components/common/inputNumber';`);
  if (needs.RangeDatePicker) lines.push(`import { RangeDatePicker } from '@/components/common/datePicker';`);
  if (needs.SingleDatePicker) lines.push(`import { SingleDatePicker } from '@/components/common/datePicker';`);
  if (needs.Textarea)        lines.push(`import { Textarea } from '@/components/common/textarea';`);
  if (needs.DotStatusText)   lines.push(`import { DotStatusText } from '@/components/common/dotStatusText';`);

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────────────
//  Template 조각 생성 헬퍼
// ─────────────────────────────────────────────────────────────────────────────

/** SearchForm 안의 각 필드 템플릿 조각 생성 */
function renderSearchField(f: FieldDef): string {
  let control = '';

  switch (f.type) {
    case 'text':
      control = `<InputText v-model="searchParams.${f.key}" placeholder="${f.label} 검색" style="width: var(--form-element-width)" />`;
      break;
    case 'number':
      control = `<InputNumber v-model="searchParams.${f.key}" placeholder="${f.label}" style="width: var(--form-element-width)" />`;
      break;
    case 'select':
    case 'radio':
    case 'badge':
      control = `<Select v-model="searchParams.${f.key}" :options="${f.key}Options" optionLabel="label" optionValue="value" placeholder="전체" style="width: var(--form-element-width)" />`;
      break;
    case 'daterange':
      control = `<RangeDatePicker v-model:from="searchParams.${f.key}From" v-model:to="searchParams.${f.key}To" />`;
      break;
    case 'date':
      control = `<SingleDatePicker v-model="searchParams.${f.key}" style="width: var(--form-element-width)" />`;
      break;
    default:
      control = `<InputText v-model="searchParams.${f.key}" style="width: var(--form-element-width)" />`;
  }

  return `          <SearchFormLabel>${f.label}</SearchFormLabel>
          <SearchFormField name="${f.key}">
            <SearchFormContent>
              ${control}
            </SearchFormContent>
          </SearchFormField>`;
}

/** DataTable Column 템플릿 조각 생성 */
function renderColumn(f: FieldDef): string {
  const styleAttr = f.width ? ` style="width: ${f.width}"` : '';

  if (f.type === 'badge') {
    return `        <Column field="${f.key}Nm" header="${f.label}"${styleAttr}>
          <template #body="{ data }">
            <DotStatusText :text="data.${f.key}Nm" :color="data.${f.key}Color" />
          </template>
        </Column>`;
  }

  const displayField = (f.type === 'select' || f.type === 'radio') ? `${f.key}Nm` : f.key;
  return `        <Column field="${displayField}" header="${f.label}"${styleAttr} />`;
}

/** Detail 패널의 상세 행 템플릿 조각 생성 */
function renderDetailRow(f: FieldDef, dataRef: string): string {
  const isFullRow = f.type === 'textarea';
  const rowClass  = isFullRow ? ' detail-row--full' : '';

  let valueContent = '';
  if (f.type === 'badge') {
    valueContent = `<DotStatusText :text="${dataRef}?.${f.key}Nm" :color="${dataRef}?.${f.key}Color" />`;
  } else if (f.type === 'select' || f.type === 'radio') {
    valueContent = `{{ ${dataRef}?.${f.key}Nm }}`;
  } else {
    valueContent = `{{ ${dataRef}?.${f.key} }}`;
  }

  return `            <div class="detail-row${rowClass}">
              <span class="detail-label">${f.label}</span>
              <span class="detail-value">${valueContent}</span>
            </div>`;
}

/** Edit 폼의 입력 행 템플릿 조각 생성 */
function renderFormRow(f: FieldDef): string {
  const requiredAttr  = f.required ? ' class="form-label required"' : ' class="form-label"';
  const isFullRow     = f.type === 'textarea';
  const rowClass      = isFullRow ? ' form-row--full' : '';

  let control = '';
  switch (f.type) {
    case 'text':
      control = `<InputText v-model="editForm.${f.key}" placeholder="${f.label} 입력"${f.required ? ' :invalid="!editForm.' + f.key + '"' : ''} />`;
      break;
    case 'number':
      control = `<InputNumber v-model="editForm.${f.key}" />`;
      break;
    case 'select':
    case 'radio':
    case 'badge':
      control = `<Select v-model="editForm.${f.key}" :options="${f.key}Options" optionLabel="label" optionValue="value" placeholder="선택"${f.required ? ' :invalid="!editForm.' + f.key + '"' : ''} />`;
      break;
    case 'date':
      control = `<SingleDatePicker v-model="editForm.${f.key}" />`;
      break;
    case 'daterange':
      control = `<RangeDatePicker v-model:from="editForm.${f.key}From" v-model:to="editForm.${f.key}To" />`;
      break;
    case 'textarea':
      control = `<Textarea v-model="editForm.${f.key}" rows="5" autoResize placeholder="${f.label} 입력" />`;
      break;
    default:
      control = `<InputText v-model="editForm.${f.key}" />`;
  }

  return `          <div class="form-row${rowClass}">
            <label${requiredAttr}>${f.label}</label>
            <div class="form-control">
              ${control}
            </div>
          </div>`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  페이지 타입별 SFC 생성
// ─────────────────────────────────────────────────────────────────────────────

function generateListDetailSFC(req: ScaffoldRequest): string {
  const { screenId, screenName, menuPath, fields } = req;
  const searchFields = fields.filter(f => f.searchable);
  const listFields   = fields.filter(f => f.listable);
  const detailFields = fields.filter(f => f.detailable);
  const editableFields = fields.filter(f => f.editable);

  const needs  = collectImportNeeds(fields);
  const assets = generateMockAssets(fields);
  const filter = generateFilterLogic(fields);
  const imports = buildImports(needs, 'list-detail');

  const menuPathComment = menuPath?.length ? menuPath.join(' > ') : screenName;
  const routePath       = `/${screenId.toUpperCase()}`;

  // ── 검색 필드 렌더링 ──────────────────────────────────────────────────────
  const searchFieldsHtml = searchFields.map(renderSearchField).join('\n');

  // ── 그리드 컬럼 렌더링 ────────────────────────────────────────────────────
  const columnsHtml = [
    `        <Column field="id" header="No" style="width: 60px" />`,
    ...listFields.map(renderColumn),
  ].join('\n');

  // ── 상세 행 렌더링 ────────────────────────────────────────────────────────
  const detailRowsHtml = detailFields.map(f => renderDetailRow(f, 'state.selectedRow')).join('\n');

  // ── EditForm 초기값 ────────────────────────────────────────────────────────
  const editFormFields = (editableFields.length ? editableFields : detailFields);
  const editFormProps  = editFormFields.map(f => {
    if (f.type === 'number') return `  ${f.key}: undefined as number | undefined`;
    if (f.type === 'daterange') return `  ${f.key}From: '',\n  ${f.key}To: ''`;
    if (f.type === 'checkbox') return `  ${f.key}: false`;
    return `  ${f.key}: ''`;
  }).join(',\n');

  const searchParamsReset = (() => {
    const props = searchFields.map(f => {
      if (f.type === 'daterange') return `${f.key}From: '', ${f.key}To: ''`;
      if (f.type === 'number') return `${f.key}: undefined`;
      return `${f.key}: ''`;
    });
    return `{ ${props.join(', ')} }`;
  })();

  return `<!-- Generated by pfy-scaffolding | ${screenName} (${screenId}) | list-detail | ${new Date().toISOString()} -->
<template>
  <StandardListTemplate
    :loading="state.loading"
    :isEmpty="filteredRows.length === 0 && !state.loading"
    :showRightDrawer="!!state.selectedRow"
    :listPanelSize="55"
  >
    <!-- ① 화면 제목: ${menuPathComment} -->
    <template #header>
      <ContentHeader title="${screenName}" />
    </template>

    <!-- ② 검색 조건 폼 -->
    <template #search-bar>
      <SearchForm>
        <SearchFormRow>
${searchFieldsHtml}
        </SearchFormRow>
        <template #buttons>
          <Button class="submit-button" label="조회" icon="pi pi-search" @click="onSearch" />
          <Button label="초기화" severity="secondary" variant="outlined" @click="onReset" />
        </template>
      </SearchForm>
    </template>

    <!-- ③ 조회 결과 그리드 -->
    <template #grid-area>
      <DataTable
        :value="pagedRows"
        :loading="state.loading"
        selectionMode="single"
        v-model:selection="state.selectedRow"
        scrollable
        scrollHeight="flex"
        @row-select="onRowSelect"
      >
${columnsHtml}
      </DataTable>
    </template>

    <!-- ④ 페이지네이션 -->
    <template #pagination>
      <Paginator
        :rows="state.pageSize"
        :totalRecords="filteredRows.length"
        :rowsPerPageOptions="[20, 50, 100]"
        @page="onPageChange"
      />
    </template>

    <!-- ⑤ 우측 상세 패널 -->
    <template #right-drawer>
      <StandardDetailTemplate :isEmpty="!state.selectedRow">
        <template #header>
          <ContentHeader title="상세 정보" />
        </template>

        <template #body>
${detailRowsHtml}
        </template>

        <template #actions>
          <Button label="수정" icon="pi pi-pencil" severity="secondary" variant="outlined" @click="onEdit" />
          <Button label="삭제" icon="pi pi-trash" severity="danger" @click="onDelete" />
        </template>
      </StandardDetailTemplate>
    </template>
  </StandardListTemplate>
</template>

<script lang="ts" setup>
${imports}

// ─────────────────── Types ──────────────────────────────────────────────────
${assets.interfaceCode}

// ─────────────────── Mock Data (API 연동 전 임시) ────────────────────────────
${assets.mockDataCode}

// ─────────────────── Options ────────────────────────────────────────────────
${assets.optionsCode}

// ─────────────────── State ──────────────────────────────────────────────────
const allRows = ref<RowItem[]>([...MOCK_DATA]);

const state = reactive({
  loading:     false,
  selectedRow: null as RowItem | null,
  pageSize:    20,
  page:        { first: 0, rows: 20 },
});

${assets.searchParamsCode}

// ─────────────────── Computed ───────────────────────────────────────────────
const filteredRows = computed<RowItem[]>(() => {
${filter}
});

const pagedRows = computed<RowItem[]>(() =>
  filteredRows.value.slice(state.page.first, state.page.first + state.pageSize)
);

// ─────────────────── Handlers ───────────────────────────────────────────────
function onSearch(): void {
  state.page        = { first: 0, rows: state.pageSize };
  state.selectedRow = null;
}

function onReset(): void {
  Object.assign(searchParams, ${searchParamsReset});
  onSearch();
}

function onRowSelect(event: { data: RowItem }): void {
  state.selectedRow = event.data;
}

function onPageChange(event: { first: number; rows: number }): void {
  state.page = event;
}

function onEdit(): void {
  // TODO: 수정 화면으로 이동 또는 모달 오픈
  console.log('[scaffold] onEdit →', state.selectedRow);
}

function onDelete(): void {
  if (!state.selectedRow) return;
  allRows.value     = allRows.value.filter(r => r.id !== state.selectedRow!.id);
  state.selectedRow = null;
}
</script>
`;
}

// ─────────────────────────────────────────────────────────────────────────────

function generateEditSFC(req: ScaffoldRequest): string {
  const { screenId, screenName, fields } = req;
  const editFields = fields.filter(f => f.editable);

  const needs   = collectImportNeeds(editFields);
  const imports = buildImports(needs, 'edit');
  const assets  = generateMockAssets(fields);

  const formRowsHtml = editFields.map(renderFormRow).join('\n');

  const editFormProps = editFields.map(f => {
    if (f.type === 'number')    return `  ${f.key}: undefined as number | undefined`;
    if (f.type === 'daterange') return `  ${f.key}From: '',\n  ${f.key}To: ''`;
    if (f.type === 'checkbox')  return `  ${f.key}: false`;
    return `  ${f.key}: ''`;
  }).join(',\n');

  const requiredChecks = editFields
    .filter(f => f.required)
    .map(f => `if (!editForm.${f.key}) { alert('${f.label}은(는) 필수 항목입니다.'); return; }`)
    .join('\n  ');

  return `<!-- Generated by pfy-scaffolding | ${screenName} (${screenId}) | edit | ${new Date().toISOString()} -->
<template>
  <StandardEditTemplate :loading="state.loading" :saving="state.saving">
    <template #header>
      <ContentHeader title="${screenName}" />
    </template>

    <template #form-body>
      <section class="form-section">
        <h3 class="form-section__title">기본 정보</h3>
${formRowsHtml}
      </section>
    </template>

    <template #actions>
      <Button label="저장" icon="pi pi-check" :loading="state.saving" @click="onSave" />
      <Button label="취소" severity="secondary" variant="outlined" @click="onCancel" />
    </template>
  </StandardEditTemplate>
</template>

<script lang="ts" setup>
${imports}

// ─────────────────── Options ────────────────────────────────────────────────
${assets.optionsCode}

// ─────────────────── State ──────────────────────────────────────────────────
const state = reactive({ loading: false, saving: false });

const editForm = reactive({
${editFormProps},
});

// ─────────────────── Handlers ───────────────────────────────────────────────
function onSave(): void {
  ${requiredChecks}
  state.saving = true;
  setTimeout(() => {
    // TODO: API 저장 호출로 교체
    console.log('[scaffold] onSave →', { ...editForm });
    state.saving = false;
  }, 800);
}

function onCancel(): void {
  // TODO: 이전 화면으로 이동
  console.log('[scaffold] onCancel');
}
</script>
`;
}

// ─────────────────────────────────────────────────────────────────────────────

function generateTabDetailSFC(req: ScaffoldRequest): string {
  const { screenId, screenName, fields, tabs = [] } = req;
  const searchFields = fields.filter(f => f.searchable);
  const listFields   = fields.filter(f => f.listable);

  const allTabFields = tabs.flatMap(t => t.fields);
  const needs        = collectImportNeeds([...fields, ...allTabFields]);
  const imports      = buildImports(needs, 'tab-detail');
  const assets       = generateMockAssets(fields);
  const filter       = generateFilterLogic(fields);

  // 탭 정의
  const tabItemsCode = tabs.map(
    t => `  { key: '${t.key}', label: '${t.label}' }`
  ).join(',\n');

  // 각 탭 패널 슬롯 콘텐츠 생성
  const tabPanels = tabs.map(tab => {
    const detailRows = tab.fields.map(f => renderDetailRow(f, 'state.selectedRow')).join('\n');
    return `    <!-- 탭: ${tab.label} -->
    <template #panel-${tab.key}>
${detailRows}
    </template>`;
  }).join('\n\n');

  const searchFieldsHtml = searchFields.map(renderSearchField).join('\n');
  const columnsHtml = [
    `        <Column field="id" header="No" style="width: 60px" />`,
    ...listFields.map(renderColumn),
  ].join('\n');

  const searchParamsReset = (() => {
    const props = searchFields.map(f => {
      if (f.type === 'daterange') return `${f.key}From: '', ${f.key}To: ''`;
      if (f.type === 'number') return `${f.key}: undefined`;
      return `${f.key}: ''`;
    });
    return `{ ${props.join(', ')} }`;
  })();

  return `<!-- Generated by pfy-scaffolding | ${screenName} (${screenId}) | tab-detail | ${new Date().toISOString()} -->
<template>
  <StandardListTemplate
    :loading="state.loading"
    :isEmpty="filteredRows.length === 0 && !state.loading"
    :showRightDrawer="!!state.selectedRow"
    :listPanelSize="45"
  >
    <template #header>
      <ContentHeader title="${screenName}" />
    </template>

    <template #search-bar>
      <SearchForm>
        <SearchFormRow>
${searchFieldsHtml}
        </SearchFormRow>
        <template #buttons>
          <Button class="submit-button" label="조회" icon="pi pi-search" @click="onSearch" />
          <Button label="초기화" severity="secondary" variant="outlined" @click="onReset" />
        </template>
      </SearchForm>
    </template>

    <template #grid-area>
      <DataTable
        :value="pagedRows"
        :loading="state.loading"
        selectionMode="single"
        v-model:selection="state.selectedRow"
        scrollable
        scrollHeight="flex"
        @row-select="onRowSelect"
      >
${columnsHtml}
      </DataTable>
    </template>

    <template #pagination>
      <Paginator
        :rows="state.pageSize"
        :totalRecords="filteredRows.length"
        :rowsPerPageOptions="[20, 50, 100]"
        @page="onPageChange"
      />
    </template>

    <!-- 우측: 탭형 상세 패널 -->
    <template #right-drawer>
      <StandardTabTemplate
        v-model="state.activeTab"
        :tabs="TABS"
        :isEmpty="!state.selectedRow"
      >
        <template #header>
          <ContentHeader title="상세 정보" />
        </template>

${tabPanels}

        <template #actions>
          <Button label="수정" icon="pi pi-pencil" severity="secondary" variant="outlined" @click="onEdit" />
        </template>
      </StandardTabTemplate>
    </template>
  </StandardListTemplate>
</template>

<script lang="ts" setup>
${imports}
import { StandardTabTemplate } from '@/components/templates';
import type { TabItem } from '@/components/templates';

// ─────────────────── Types ──────────────────────────────────────────────────
${assets.interfaceCode}

// ─────────────────── Mock Data ───────────────────────────────────────────────
${assets.mockDataCode}

// ─────────────────── Options / Tabs ─────────────────────────────────────────
${assets.optionsCode}

const TABS: TabItem[] = [
${tabItemsCode},
];

// ─────────────────── State ──────────────────────────────────────────────────
const allRows = ref<RowItem[]>([...MOCK_DATA]);

const state = reactive({
  loading:     false,
  selectedRow: null as RowItem | null,
  activeTab:   '${tabs[0]?.key ?? 'tab0'}',
  pageSize:    20,
  page:        { first: 0, rows: 20 },
});

${assets.searchParamsCode}

// ─────────────────── Computed ───────────────────────────────────────────────
const filteredRows = computed<RowItem[]>(() => {
${filter}
});

const pagedRows = computed<RowItem[]>(() =>
  filteredRows.value.slice(state.page.first, state.page.first + state.pageSize)
);

// ─────────────────── Handlers ───────────────────────────────────────────────
function onSearch(): void {
  state.page        = { first: 0, rows: state.pageSize };
  state.selectedRow = null;
}

function onReset(): void {
  Object.assign(searchParams, ${searchParamsReset});
  onSearch();
}

function onRowSelect(event: { data: RowItem }): void {
  state.selectedRow = event.data;
  state.activeTab   = '${tabs[0]?.key ?? 'tab0'}';
}

function onPageChange(event: { first: number; rows: number }): void {
  state.page = event;
}

function onEdit(): void {
  console.log('[scaffold] onEdit →', state.selectedRow);
}
</script>
`;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Public Entry Point
// ─────────────────────────────────────────────────────────────────────────────

/** 스캐폴딩 요청으로부터 완성된 Vue SFC 문자열을 생성 */
export function generateVuePage(req: ScaffoldRequest): string {
  switch (req.pageType) {
    case 'list-detail':
    case 'list':
      return generateListDetailSFC(req);
    case 'edit':
      return generateEditSFC(req);
    case 'tab-detail':
      return generateTabDetailSFC(req);
    default:
      return generateListDetailSFC(req);
  }
}
