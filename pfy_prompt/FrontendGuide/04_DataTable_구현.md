# 04. DataTable 구현

## 📋 이 단계의 목적

**DataTable2 래퍼 컴포넌트**를 사용하여 DataTable을 구현합니다.

> ⚠️ **CRITICAL**: pfy-front 프로젝트는 `primevue/datatable`을 직접 사용하지 않습니다.
> 반드시 `@/components/common/dataTable2`의 **DataTable2 래퍼**를 사용해야 합니다.
> DataTable2 래퍼는 DataTableHeader(제목, 건수, 유틸리티 버튼)를 자동으로 렌더링합니다.

---

## 📝 Step 1: DataTable2 래퍼 vs PrimeVue DataTable 차이

| 구분 | ❌ PrimeVue DataTable (사용 금지) | ✅ DataTable2 래퍼 (사용 필수) |
|------|----------------------------------|-------------------------------|
| Import | `import DataTable from 'primevue/datatable'` | `import { DataTable } from '@/components/common/dataTable2'` |
| 컬럼 정의 | `<Column>` 자식 요소 | `:columns="columns"` prop |
| 헤더 영역 | 없음 | DataTableHeader 자동 렌더링 |
| 건수 표시 | 없음 | `:totalCount` prop |
| 체크박스 | `selectionMode="multiple"` Column | `:enableRowCheck="true"` prop |
| 유틸리티 버튼 | 없음 | `:utilOptions` prop |
| 컬럼 타입 | 자유 정의 | `TableColumn` from `dataTable2/types` |

### ⚠️ CRITICAL: `<Column>` 자식 요소는 DataTable2에서 무시됨

```vue
<!-- ❌ WRONG — <Column> 자식은 DataTable2 래퍼에서 완전히 무시됨 -->
<DataTable :value="rows" ...>
  <Column field="userId" header="사용자ID" />
  <Column field="userName" header="사용자명" />
</DataTable>

<!-- ✅ CORRECT — :columns prop으로 전달 -->
<DataTable
  :value="displayRows"
  :columns="columns"
  dataKey="userId"
  ...
/>
```

---

## 📝 Step 2: 파일 구조

```
src/pages/{module}/{category}/{screenId}/
└── components/
    └── {screenId}DataTable/
        ├── {ScreenId}DataTable.vue       ← DataTable2 래퍼 사용
        ├── {ScreenId}DataTable.scss      ← GPU 가속 CSS
        └── utils/
            └── index.ts                  ← getColumns(), getRows() — TableColumn 타입 사용
```

---

## 📝 Step 3: TableColumn 타입 (CRITICAL!)

DataTable2는 `TableColumn` 타입만 허용합니다. 커스텀 컬럼 타입 정의 **금지**.

```typescript
// @/components/common/dataTable2/types.ts
export type TableColumn = {
  objectId: string;    // ⭐ 필수! field와 동일한 값 사용
  field: string;
  header: string;
  width?: string;      // "140px" 형태 (minWidth 아님!)
  columnClass?: string; // 헤더 정렬: 'left' | 'center' | 'right'
  rowClass?: string;   // 바디 셀 정렬: 'left' | 'center' | 'right'
  visible?: boolean;   // ⭐ 필수! true로 설정해야 컬럼이 표시됨
  frozen?: boolean;    // 좌측 고정
  required?: boolean;  // 필수값 표시
};
```

**⚠️ 중요 규칙**:
- `objectId`는 반드시 설정 (보통 `field`와 동일한 값)
- `visible: true`가 없으면 컬럼이 화면에 표시되지 않음
- `width`는 `"140px"` 형태 (`minWidth` 아님)
- `columnClass`/`rowClass`는 `'left'|'center'|'right'` 문자열

---

## 📝 Step 4: utils/index.ts 작성

```typescript
// {ScreenId}DataTable/utils/index.ts

import type { TableColumn } from '@/components/common/dataTable2/types';
import type { CpmsEduProgLstResDto } from '@/api/pages/edu/prog/types';

// ⭐ 날짜 포맷팅 전처리를 위한 DisplayRow 타입
export type CpmsEduProgLstDisplayRow = CpmsEduProgLstResDto & {
  eduDateFormatted?: string;
  createdAtFormatted?: string;
};

// 날짜 포맷팅 헬퍼 (utils 내부용)
const formatDate = (value?: string | null): string => {
  if (!value) return '';
  const pure = value.replaceAll('-', '').slice(0, 8);
  if (pure.length !== 8) return value;
  return `${pure.slice(0, 4)}-${pure.slice(4, 6)}-${pure.slice(6, 8)}`;
};

// ⭐⭐⭐ CRITICAL: TableColumn 타입 사용, objectId와 visible 필수!
export const getColumns = (): TableColumn[] => [
  {
    objectId: 'userId',      // ⭐ field와 동일
    field: 'userId',
    header: '사용자 ID',
    width: '140px',
    frozen: true,
    columnClass: 'left',    // 헤더 왼쪽 정렬
    rowClass: 'left',       // 바디 왼쪽 정렬
    visible: true,           // ⭐ 필수!
  },
  {
    objectId: 'userName',
    field: 'userName',
    header: '사용자명',
    width: '140px',
    columnClass: 'left',
    rowClass: 'left',
    visible: true,
  },
  {
    objectId: 'deptName',
    field: 'deptName',
    header: '부서명',
    width: '180px',
    columnClass: 'left',
    rowClass: 'left',
    visible: true,
  },
  {
    objectId: 'eduDateFormatted',  // ⭐ 포맷팅된 필드 사용
    field: 'eduDateFormatted',
    header: '교육일자',
    width: '130px',
    columnClass: 'center',
    rowClass: 'center',
    visible: true,
  },
  {
    objectId: 'eduStatus',
    field: 'eduStatus',
    header: '교육상태',
    width: '120px',
    columnClass: 'center',
    rowClass: 'center',
    visible: true,
  },
];

// ⭐ 날짜 포맷팅 전처리 — getRows()에서 1회 처리 (성능 핵심!)
//
// ❌ DON'T: 템플릿 슬롯 방식 (성능 최악)
//   <Column field="eduDate">
//     <template #body="{ data }">{{ formatDate(data.eduDate) }}</template>
//   </Column>
//   → 렌더링·스크롤·hover 시마다 호출: 1000행 × 5컬럼 = 5000번+
//
// ✅ DO: getRows() 전처리 방식 (현재)
//   → 데이터 로딩 시 1회만 호출: 1000번
export const getRows = (data?: CpmsEduProgLstResDto[] | null): CpmsEduProgLstDisplayRow[] => {
  return (data ?? []).map((row) => ({
    ...row,
    eduDateFormatted: formatDate(row.eduDate),
    createdAtFormatted: formatDate(row.createdAt),
  }));
};
```

---

## 📝 Step 5: DataTable2 래퍼 사용 (완성 코드)

```vue
<!-- CpmsEduProgLstDataTable.vue -->
<template>
  <div class="datatable-container">
    <DataTable
      :value="displayRows"
      :columns="columns"
      dataKey="userId"
      :loading="loading"
      title="교육 이력 목록"
      :totalCount="totalRecords"
      :enableRowCheck="true"
      :utilOptions="['filter', 'settings', 'reset', 'downloadExcel']"
      :scrollHeight="'540px'"
      :virtualScrollerOptions="{ itemSize: 46 }"
    />
  </div>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue';
import { DataTable } from '@/components/common/dataTable2';
import type { CpmsEduProgLstResDto } from '@/api/pages/edu/prog/types';
import { getColumns, getRows, type CpmsEduProgLstDisplayRow } from './utils';

interface Props {
  fetchedMainData: CpmsEduProgLstResDto[] | null;
  loading: boolean;
  totalRecords?: number;
  rows?: number;
  first?: number;
}

const props = withDefaults(defineProps<Props>(), {
  fetchedMainData: null,
  loading: false,
  totalRecords: 0,
  rows: 20,
  first: 0,
});

// ⭐ 컬럼 정의 — getColumns()에서 TableColumn[] 반환
const columns = getColumns();

// ⭐ 데이터 변환 — getRows()에서 날짜 포맷팅 전처리
const displayRows = computed(() => getRows(props.fetchedMainData));
</script>

<style scoped lang="scss" src="./CpmsEduProgLstDataTable.scss"></style>
```

---

## 📝 Step 6: DataTableHeader 자동 렌더링 props

DataTable2 래퍼는 DataTableHeader를 자동으로 렌더링합니다.
아래 props로 DataTableHeader의 내용을 제어합니다.

### 6.1 title — 테이블 제목

```vue
<!-- ✅ 문자열 전달 -->
<DataTable title="교육 이력 목록" ... />

<!-- ✅ objectId가 필요한 경우 -->
<DataTable :title="{ objectId: 'CpmsEduProgLst.title', content: '교육 이력 목록' }" ... />
```

### 6.2 enableRowCheck — 체크박스 컬럼

```vue
<!-- ✅ CORRECT: DataTable2 방식 — enableRowCheck prop -->
<DataTable :enableRowCheck="true" ... />

<!-- ❌ WRONG: PrimeVue 방식 — Column selectionMode (DataTable2에서 무시됨) -->
<DataTable selectionMode="multiple" ...>
  <Column selectionMode="multiple" />
</DataTable>
```

`enableRowCheck="true"`를 설정하면:
- 체크박스 컬럼 자동 추가
- DataTableHeader에 "Total X Items / selected Y" 표시

### 6.3 utilOptions — 유틸리티 버튼

```typescript
type UtilOptions =
  | 'addRow'          // 행 추가
  | 'deleteRow'       // 행 삭제
  | 'copyInsertRow'   // 행 복사 추가
  | 'filter'          // 필터 토글
  | 'settings'        // 컬럼 설정
  | 'uploadExcel'     // 엑셀 업로드
  | 'downloadExcel'   // 엑셀 다운로드
  | 'downloadTemplate'// 엑셀 양식 다운로드
  | 'reset';          // 리셋
```

```vue
<!-- 조회 전용 화면: 필터, 설정, 리셋, 엑셀다운로드 -->
<DataTable :utilOptions="['filter', 'settings', 'reset', 'downloadExcel']" ... />

<!-- CRUD 화면: 행 추가/삭제 포함 -->
<DataTable :utilOptions="['addRow', 'deleteRow', 'filter', 'settings', 'reset']" ... />
```

### 6.4 totalCount — 총 건수

```vue
<!-- ✅ CORRECT -->
<DataTable :totalCount="totalRecords" ... />

<!-- enableRowCheck + totalCount 조합:
     DataTableHeader에 "Total 100 Items / selected 3" 표시 -->
```

---

## 📝 Step 7: 페이지네이션 (paginator)

DataTable2 래퍼는 PrimeVue DataTable의 attr을 그대로 통과시킵니다.
페이지네이션이 필요한 경우 직접 전달합니다.

```vue
<DataTable
  :value="displayRows"
  :columns="columns"
  dataKey="id"
  :loading="loading"
  :totalCount="totalRecords"
  :enableRowCheck="true"
  :utilOptions="['filter', 'settings', 'reset', 'downloadExcel']"
  :scrollHeight="'540px'"
  :virtualScrollerOptions="{ itemSize: 46 }"
  paginator
  :rows="rows"
  :first="first"
  :totalRecords="totalRecords"
  lazy
  @page="handlePage"
/>
```

---

## 📝 Step 8: GPU 가속 SCSS

```scss
// CpmsEduProgLstDataTable.scss

.datatable-container {
  width: 100%;
  height: 100%;

  :deep(.p-datatable) {
    .p-datatable-tbody {
      tr {
        // ⭐ GPU 가속: 행 hover 시 리페인트 최소화 (FPS 15 → 60)
        will-change: background-color;
        transition: background-color 0.2s;

        // ⭐ 선택된 행에는 hover 스타일 적용 안 함
        &:hover:not(.p-datatable-row-selected) {
          background-color: var(--primary-50);
        }
      }

      tr > td {
        // ⭐ CSS containment: 한 셀 변경 시 전체 테이블 재계산 방지
        contain: layout style;
      }
    }
  }
}
```

### 8.1 각 속성 설명

#### A. `will-change: background-color`

```scss
tr {
  will-change: background-color;
}
```

**효과**:
- GPU에 별도 레이어 생성 → hover 시 리페인트 최소화
- 행 hover FPS: ~15 FPS → ~60 FPS

**주의**: 너무 많은 요소에 사용하면 GPU 메모리 증가

#### B. `contain: layout style`

```scss
td {
  contain: layout style;
}
```

**효과**:
- 각 셀의 레이아웃을 독립적으로 처리
- 한 셀 내용 변경 시 전체 테이블 리플로우 방지

#### C. `:hover:not(.p-datatable-row-selected)`

```scss
// ✅ CORRECT — 선택된 행 제외
&:hover:not(.p-datatable-row-selected) {
  background-color: var(--primary-50);
}

// ❌ WRONG — 선택된 행도 hover 색상이 덮어씀
&:hover {
  background-color: var(--primary-50);
}
```

### 8.2 헤더 정렬 CSS 순서 (CRITICAL!)

`columnClass`/`rowClass`로 설정한 left/center/right가 제대로 적용되려면 CSS 선언 순서가 중요합니다.

```scss
:deep(.p-datatable) {
  // ⚠️ 순서 중요: 전체 기본값 먼저
  .p-datatable-column-header-content {
    justify-content: center;  // ← 기본: 중앙 정렬
  }

  // ⚠️ 순서 중요: 특정 클래스 나중에 (override)
  .left .p-datatable-column-header-content {
    justify-content: flex-start;
  }

  .right .p-datatable-column-header-content {
    justify-content: flex-end;
  }
}
```

```scss
// ❌ WRONG — 순서가 반대면 .left가 center에 덮어씌워짐
.left .p-datatable-column-header-content {
  justify-content: flex-start;
}
.p-datatable-column-header-content {
  justify-content: center;  // ← 이 선언이 나중이므로 .left 무시됨
}
```

---

## 📝 Step 9: 가상 스크롤링 성능 원리

DataTable2에서 `:scrollHeight` / `:virtualScrollerOptions`는 내부 PrimeVue DataTable에 그대로 전달됩니다.
대용량 데이터를 다룰 때 **반드시 설정**해야 합니다.

### 9.1 성능 비교

| 설정 | DOM 노드 수 | 렌더링 시간 | 스크롤 FPS |
|------|------------|-------------|-----------|
| `scrollHeight` 미설정 | 27,000개 (1000행 × 27컬럼) | ~3초 | ~15 FPS |
| `:scrollHeight="'540px'"` + `:virtualScrollerOptions` | ~300개 | ~100ms | ~60 FPS |

### 9.2 올바른 설정

```vue
<!-- ✅ CORRECT -->
<DataTable
  :scrollHeight="'540px'"
  :virtualScrollerOptions="{ itemSize: 46 }"
  ...
/>
```

- `scrollHeight`: 고정 픽셀 값 → 보이는 영역만 DOM에 렌더링 (약 12행)
- `virtualScrollerOptions.itemSize`: 각 행의 높이(px). 개발자 도구에서 `tr` 높이 확인 후 설정

```scss
// 개발자 도구에서 실제 행 높이 확인
.p-datatable-tbody > tr {
  height: 46px;  // ← 이 값을 itemSize에 사용
}
```

### 9.3 scrollHeight 금지 값

```vue
<!-- ❌ WRONG — 모든 행을 DOM에 렌더링하므로 1000행 시 극도로 느림 -->
<DataTable scrollHeight="flex" ...>
```

## ✅ 구현 완료 체크리스트

### 컬럼 정의 (utils/index.ts)
- [ ] `TableColumn` 타입을 `'@/components/common/dataTable2/types'`에서 import
- [ ] 커스텀 컬럼 타입 정의 없음 (TableColumn만 사용)
- [ ] 모든 컬럼에 `objectId` 필드 설정 (field와 동일한 값)
- [ ] 모든 컬럼에 `visible: true` 설정
- [ ] `width`는 `"140px"` 형태 (minWidth 아님)
- [ ] 날짜 포맷팅은 `getRows()`에서 전처리 (템플릿 슬롯 사용 금지)
- [ ] 포맷팅된 컬럼은 `field: 'someDateFormatted'`처럼 _Formatted 접미사 사용

### DataTable.vue
- [ ] `import { DataTable } from '@/components/common/dataTable2'`
- [ ] `Column from 'primevue/column'` import 없음
- [ ] `<Column>` 자식 요소 없음
- [ ] `:columns="columns"` prop 전달 (getColumns() 결과)
- [ ] `:value="displayRows"` (computed from getRows())
- [ ] `title` prop 설정
- [ ] `:enableRowCheck` prop 설정 (체크박스 필요 시)
- [ ] `:utilOptions` prop 설정
- [ ] `:totalCount` prop 설정
- [ ] `:scrollHeight="'540px'"` (고정 높이, `"flex"` 금지)
- [ ] `:virtualScrollerOptions="{ itemSize: 46 }"` (itemSize는 실제 tr 높이)

### 성능 검증
- [ ] 1000개 이상 데이터 로딩 시 렌더링 속도 확인
- [ ] 스크롤 성능 확인 (60 FPS 목표)
- [ ] 날짜 포맷팅이 템플릿이 아닌 getRows()에서 처리되고 있는지 확인

### SCSS
- [ ] `will-change: background-color` on tr
- [ ] `contain: layout style` on td
- [ ] `:hover:not(.p-datatable-row-selected)` hover 선택자
- [ ] 헤더 정렬 CSS 순서: 전체(center) 먼저, .left/.right 나중

---

## 🐛 자주 발생하는 에러

### 1. 컬럼이 하나도 표시되지 않음

**증상**: DataTable 테이블 영역이 비어 있거나 헤더가 없음

**원인 A**: `<Column>` 자식 요소 사용 (DataTable2에서 무시됨)
```vue
<!-- ❌ WRONG -->
<DataTable :value="rows" ...>
  <Column field="userId" header="사용자ID" />  ← 무시됨!
</DataTable>
```

**원인 B**: `visible: true` 누락
```typescript
// ❌ WRONG — visible 없으면 컬럼 미표시
{ objectId: 'userId', field: 'userId', header: '사용자ID', width: '140px' }

// ✅ CORRECT
{ objectId: 'userId', field: 'userId', header: '사용자ID', width: '140px', visible: true }
```

**원인 C**: `:columns` prop 미전달
```vue
<!-- ❌ WRONG -->
<DataTable :value="rows" ... />

<!-- ✅ CORRECT -->
<DataTable :value="rows" :columns="columns" ... />
```

### 2. DataTableHeader (제목, 건수, 버튼)가 표시되지 않음

**증상**: 테이블 위에 헤더 영역이 없음

**원인**: DataTable2 import 없이 PrimeVue DataTable 직접 사용
```typescript
// ❌ WRONG
import DataTable from 'primevue/datatable'  // 또는
import DataTable from '@/components/common/dataTable2/DataTable.vue'  // 직접 경로

// ✅ CORRECT
import { DataTable } from '@/components/common/dataTable2'
```

### 3. objectId 없어서 컬럼 정렬/설정 오작동

**증상**: 컬럼 설정 레이어에서 컬럼이 표시되지 않거나 에러 발생

**원인**: `objectId` 누락
```typescript
// ❌ WRONG
{ field: 'userId', header: '사용자ID', visible: true }

// ✅ CORRECT
{ objectId: 'userId', field: 'userId', header: '사용자ID', visible: true }
```

### 4. 커스텀 컬럼 타입 사용

**원인**: TableColumn 대신 커스텀 타입 정의
```typescript
// ❌ WRONG — 커스텀 타입 정의
interface MyColumn {
  field: string;
  header: string;
  minWidth?: string;    // ← DataTable2 무시
  align?: 'center';    // ← DataTable2 무시
  selectionMode?: 'multiple';  // ← DataTable2 무시
}

// ✅ CORRECT
import type { TableColumn } from '@/components/common/dataTable2/types';
```

### 5. 스크롤이 느리거나 로딩이 오래 걸림

**증상**: 대용량 데이터(500건 이상) 로딩 시 화면이 굳거나 스크롤이 버벅임

**원인 A**: `scrollHeight` 미설정 또는 `"flex"` 사용
```vue
<!-- ❌ WRONG — 모든 행을 DOM에 렌더링 -->
<DataTable ... />                          <!-- scrollHeight 없음 -->
<DataTable :scrollHeight="'flex'" ... />   <!-- flex는 가상 스크롤 비활성화 -->

<!-- ✅ CORRECT -->
<DataTable :scrollHeight="'540px'" :virtualScrollerOptions="{ itemSize: 46 }" ... />
```

**원인 B**: 날짜 포맷팅을 템플릿에서 처리
```typescript
// ❌ WRONG — utils/index.ts에서 Column 정의 시 template 슬롯 방식 유도
// → 렌더링·스크롤·hover마다 formatDate 호출

// ✅ CORRECT — getRows()에서 전처리
export const getRows = (data) => data.map(row => ({
  ...row,
  eduDateFormatted: formatDate(row.eduDate), // 로딩 시 1회만 실행
}));
```

---

## 🎯 다음 단계

DataTable 구현이 완료되었다면 **[05_SumGrid_ProgressBar_구현.md](./05_SumGrid_ProgressBar_구현.md)**로 이동하세요.
