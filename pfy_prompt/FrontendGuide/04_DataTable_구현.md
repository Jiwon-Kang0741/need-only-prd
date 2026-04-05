# 04. DataTable 구현

## 📋 이 단계의 목적

대용량 데이터를 빠르게 표시하는 **DataTable 컴포넌트**를 구현합니다.

## 📝 Step 1: 성능 최적화 필수 사항 (READ FIRST!)

### ⚠️ CRITICAL: 성능 최적화 없이는 극도로 느림!

**문제 상황**:
- 1000개 행 × 27개 컬럼 = 27,000개 셀
- 날짜 포맷팅 5개 컬럼 × 1000개 행 = 5,000번 함수 호출/렌더링
- 행 hover 시 전체 테이블 리플로우

**해결 방법**:
1. ✅ **가상 스크롤링** (Virtual Scrolling)
2. ✅ **날짜 포맷팅 전처리** (Pre-processing)
3. ✅ **GPU 가속** (will-change CSS)
4. ✅ **CSS Containment** (layout isolation)

## 📝 Step 2: 기본 구조 생성

### 2.1 파일 생성

```bash
# 폴더 생성
mkdir -p src/pages/sy/ds/pmdp010/components/pmdp010DataTable

# 파일 생성 (SCSS 포함!)
touch src/pages/sy/ds/pmdp010/components/pmdp010DataTable/PMDP010DataTable.vue
touch src/pages/sy/ds/pmdp010/components/pmdp010DataTable/PMDP010DataTable.scss
```

**⚠️ 중요**: SCSS 파일은 필수입니다! 성능 최적화 CSS를 포함합니다.

### 2.2 기본 템플릿

```vue
<!-- PMDP010DataTable.vue -->
<template>
  <div class="datatable-container">
    <DataTable
      v-model:selection="selectedRows"
      :value="fetchedMainData"
      scrollable
      scrollHeight="540px"
      :virtualScrollerOptions="{ itemSize: 46 }"
      selectionMode="multiple"
      dataKey="ASK_NO"
      :loading="loading"
    >
      <!-- 컬럼들 -->
    </DataTable>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, nextTick } from 'vue';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import type { PMDP010MainData } from '@/api/pages/sy/ds/types';

// Props
interface Props {
  fetchedMainData: PMDP010MainData[] | null;
  loading: boolean;
}

const props = defineProps<Props>();

// 선택된 행
const selectedRows = ref<PMDP010MainData[]>([]);
</script>

<style scoped lang="scss" src="./PMDP010DataTable.scss"></style>
```

**⚠️ 중요**: `<style>` 태그에 SCSS 파일을 연결해야 성능 최적화 CSS가 적용됩니다!

## 📝 Step 3: 가상 스크롤링 구현 (CRITICAL!)

### 3.1 설정 방법

```vue
<DataTable
  scrollable
  scrollHeight="540px"
  :virtualScrollerOptions="{ itemSize: 46 }"
>
```

### 3.2 각 속성 설명

#### A. `scrollable`
- 스크롤 활성화 필수

#### B. `scrollHeight="540px"`
⚠️ **DO**: 고정 높이 사용
```vue
<!-- ✅ CORRECT -->
<DataTable scrollHeight="540px">
```

⚠️ **DON'T**: flex 높이 사용
```vue
<!-- ❌ WRONG - 모든 행을 렌더링하므로 느림 -->
<DataTable scrollHeight="flex">
```

**이유**: 
- `flex`: 모든 행을 DOM에 렌더링 (1000개 행 = 1000개 DOM 노드)
- `540px`: 보이는 영역만 렌더링 (약 12개 행만 DOM에 존재)

#### C. `virtualScrollerOptions="{ itemSize: 46 }"`
- `itemSize`: 각 행의 높이 (px)
- PMDP010의 경우 행 높이 46px

**높이 계산 방법**:
```scss
// 개발자 도구에서 확인
.p-datatable-tbody > tr {
  height: 46px;  // ← 이 값 사용
}
```

### 3.3 성능 비교

| 설정 | DOM 노드 수 | 렌더링 시간 | 스크롤 FPS |
|------|-------------|-------------|-----------|
| scrollHeight="flex" | 27,000개 | ~3초 | ~15 FPS |
| scrollHeight="540px" + virtual | ~300개 | ~100ms | ~60 FPS |

## 📝 Step 4: 컬럼 정의

### 4.1 선택 컬럼 (체크박스)

```vue
<Column selectionMode="multiple" frozen headerStyle="width: 3rem" />
```

**frozen**: 좌측 고정 (스크롤 시에도 보임)

### 4.2 텍스트 컬럼

```vue
<Column field="CONT_NO" header="계약번호" style="min-width: 150px" />
<Column field="BUSN_SC" header="부체계" style="min-width: 100px" />
<Column field="ASK_NO" header="의뢰번호" style="min-width: 120px" />
```

### 4.3 날짜 컬럼 (CRITICAL!)

#### ⚠️ DO: 전처리 방식

```vue
<!-- ✅ CORRECT - 포맷팅된 필드 사용 -->
<Column field="ASK_DT_FORMATTED" header="의뢰일자" style="min-width: 120px" />
<Column field="REQ_DT_FORMATTED" header="요청일자" style="min-width: 120px" />
```

```typescript
// watch에서 한 번만 포맷팅
watch(
  () => props.fetchedMainData,
  async (newData) => {
    if (!newData) return;
    
    await nextTick();
    
    newData.forEach((row: any) => {
      if (row.ASK_DT) {
        row.ASK_DT_FORMATTED = formatDate(row.ASK_DT, 'YYYYMMDD', 'YYYY-MM-DD');
      }
      if (row.REQ_DT) {
        row.REQ_DT_FORMATTED = formatDate(row.REQ_DT, 'YYYYMMDD', 'YYYY-MM-DD');
      }
      // ... 나머지 날짜 필드
    });
  },
  { immediate: true }
);
```

#### ⚠️ DON'T: 템플릿 슬롯 방식

```vue
<!-- ❌ WRONG - 렌더링 시마다 함수 호출 -->
<Column field="ASK_DT" header="의뢰일자">
  <template #body="{ data }">
    {{ formatDate(data.ASK_DT, 'YYYYMMDD', 'YYYY-MM-DD') }}
  </template>
</Column>
```

**성능 차이**:
- 전처리: 1000번 호출 (데이터 로딩 시 1회)
- 템플릿 슬롯: 5000번+ 호출 (렌더링, 스크롤, hover마다)

### 4.4 중앙 정렬 컬럼

```vue
<Column
  field="PRG_STAT_NM"
  header="진행상태"
  style="min-width: 120px"
  headerClass="center"
  bodyClass="center"
/>
```

**CSS**:
```scss
.center {
  text-align: center;
}
```

### 4.5 우측 정렬 컬럼 (숫자)

```vue
<Column
  field="ASK_QTY"
  header="수량"
  style="min-width: 100px"
  headerClass="right"
  bodyClass="right"
/>
```

## 📝 Step 5: 날짜 포맷팅 전처리

### 5.1 formatDate 유틸리티

```typescript
// @/utils/dateUtils.ts
export function formatDate(
  value: string | null | undefined,
  fromFormat: string,
  toFormat: string
): string {
  if (!value) return '';
  
  // YYYYMMDD → YYYY-MM-DD
  if (fromFormat === 'YYYYMMDD' && toFormat === 'YYYY-MM-DD') {
    if (value.length === 8) {
      return `${value.substring(0, 4)}-${value.substring(4, 6)}-${value.substring(6, 8)}`;
    }
  }
  
  // 추가 포맷 지원
  // ...
  
  return value;
}
```

### 5.2 watch 구현

```typescript
import { formatDate } from '@/utils/dateUtils';

watch(
  () => props.fetchedMainData,
  async (newData) => {
    if (!newData) return;
    
    // ⭐ nextTick: DOM 업데이트 후 실행
    await nextTick();
    
    newData.forEach((row: any) => {
      // 의뢰일자
      if (row.ASK_DT) {
        row.ASK_DT_FORMATTED = formatDate(row.ASK_DT, 'YYYYMMDD', 'YYYY-MM-DD');
      }
      
      // 요청일자
      if (row.REQ_DT) {
        row.REQ_DT_FORMATTED = formatDate(row.REQ_DT, 'YYYYMMDD', 'YYYY-MM-DD');
      }
      
      // 조달요청일자
      if (row.ASK_PRCR_COMPL_REQ_DT) {
        row.ASK_PRCR_COMPL_REQ_DT_FORMATTED = formatDate(
          row.ASK_PRCR_COMPL_REQ_DT,
          'YYYYMMDD',
          'YYYY-MM-DD'
        );
      }
      
      // ... 나머지 날짜 필드
    });
  },
  { immediate: true }  // ⭐ 초기 로딩 시에도 실행
);
```

### 5.3 왜 nextTick이 필요한가?

```typescript
// ❌ WRONG - nextTick 없이
watch(() => props.fetchedMainData, (newData) => {
  newData.forEach(row => {
    row.ASK_DT_FORMATTED = formatDate(row.ASK_DT, ...);
  });
});
// → DataTable이 아직 렌더링 전이므로 깜빡임 발생

// ✅ CORRECT - nextTick 사용
watch(() => props.fetchedMainData, async (newData) => {
  await nextTick();  // ← DOM 업데이트 대기
  newData.forEach(row => {
    row.ASK_DT_FORMATTED = formatDate(row.ASK_DT, ...);
  });
});
// → DOM 업데이트 후 포맷팅하므로 부드럽게 표시
```

## 📝 Step 6: GPU 가속 CSS (CRITICAL!)

### 6.1 전역 CSS 수정

```scss
// tomms-lite-front/src/styles/components/dataTable.scss

.p-datatable {
  .p-datatable-tbody {
    tr {
      // ⭐ GPU 가속: 행 hover 성능 개선
      will-change: background-color;
      transition: background-color 0.2s;
      
      // ⭐ 최적화된 hover 선택자
      &:hover:not(.p-datatable-row-selected) {
        background-color: var(--primary-50);
      }
    }
  }
  
  .p-datatable-tbody > tr > td,
  .p-datatable-thead > tr > th {
    // ⭐ CSS containment: 레이아웃 재계산 방지
    contain: layout style;
  }
}
```

### 6.2 각 속성 설명

#### A. `will-change: background-color`
```scss
tr {
  will-change: background-color;
}
```

**효과**:
- GPU에 레이어 생성
- hover 시 리페인트 최소화
- FPS 15 → 60 개선

**주의**: 너무 많이 사용하면 메모리 증가

#### B. `contain: layout style`
```scss
td, th {
  contain: layout style;
}
```

**효과**:
- 각 셀의 레이아웃을 독립적으로 처리
- 한 셀 변경 시 전체 테이블 재계산 방지

#### C. `&:hover:not(.p-datatable-row-selected)`
```scss
// ✅ CORRECT - 선택된 행 제외
&:hover:not(.p-datatable-row-selected) {
  background-color: var(--primary-50);
}

// ❌ WRONG - 선택된 행도 hover 적용
&:hover {
  background-color: var(--primary-50);
}
```

### 6.3 성능 측정

```javascript
// Chrome DevTools > Performance 프로파일링
// Before: 행 hover 시 프레임 드롭 (15-20 FPS)
// After: 부드러운 애니메이션 (55-60 FPS)
```

## 📝 Step 7: 헤더 정렬

### 7.1 중앙 정렬

```scss
// ⭐ CRITICAL: 순서 중요!
.p-datatable {
  // ⚠️ DO: 먼저 전체 중앙 정렬
  .p-datatable-column-header-content {
    justify-content: center;
  }
  
  // ⚠️ DO: 그 다음 특정 컬럼 좌/우 정렬
  .left .p-datatable-column-header-content {
    justify-content: flex-start;
  }
  
  .right .p-datatable-column-header-content {
    justify-content: flex-end;
  }
}
```

### 7.2 왜 순서가 중요한가?

```scss
// ❌ WRONG - 순서가 반대
.left .p-datatable-column-header-content {
  justify-content: flex-start;
}

.p-datatable-column-header-content {
  justify-content: center;  // ← 이게 나중이므로 .left를 덮어씀
}

// ✅ CORRECT - 전체 먼저, 특정 나중
.p-datatable-column-header-content {
  justify-content: center;
}

.left .p-datatable-column-header-content {
  justify-content: flex-start;  // ← 이게 나중이므로 .left에 적용
}
```

## 📝 Step 8: 완성 코드

```vue
<template>
  <div class="datatable-container">
    <DataTable
      v-model:selection="selectedRows"
      :value="fetchedMainData"
      scrollable
      scrollHeight="540px"
      :virtualScrollerOptions="{ itemSize: 46 }"
      selectionMode="multiple"
      dataKey="ASK_NO"
      :loading="loading"
      stripedRows
      showGridlines
    >
      <!-- 선택 컬럼 -->
      <Column
        selectionMode="multiple"
        frozen
        headerStyle="width: 3rem"
      />
      
      <!-- 텍스트 컬럼 -->
      <Column
        field="CONT_NO"
        header="계약번호"
        style="min-width: 150px"
        frozen
      />
      
      <Column
        field="BUSN_SC"
        header="부체계"
        style="min-width: 100px"
      />
      
      <Column
        field="ASK_NO"
        header="의뢰번호"
        style="min-width: 120px"
      />
      
      <!-- 날짜 컬럼 (포맷팅 전처리) -->
      <Column
        field="ASK_DT_FORMATTED"
        header="의뢰일자"
        style="min-width: 120px"
        headerClass="center"
        bodyClass="center"
      />
      
      <Column
        field="REQ_DT_FORMATTED"
        header="요청일자"
        style="min-width: 120px"
        headerClass="center"
        bodyClass="center"
      />
      
      <!-- 진행상태 -->
      <Column
        field="PRG_STAT_NM"
        header="진행상태"
        style="min-width: 120px"
        headerClass="center"
        bodyClass="center"
      />
      
      <!-- 숫자 컬럼 -->
      <Column
        field="ASK_QTY"
        header="수량"
        style="min-width: 100px"
        headerClass="right"
        bodyClass="right"
      />
      
      <!-- ... 나머지 컬럼 -->
    </DataTable>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, nextTick } from 'vue';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import type { PMDP010MainData } from '@/api/pages/sy/ds/types';
import { formatDate } from '@/utils/dateUtils';

// Props
interface Props {
  fetchedMainData: PMDP010MainData[] | null;
  loading: boolean;
}

const props = defineProps<Props>();

// 선택된 행
const selectedRows = ref<PMDP010MainData[]>([]);

// ⭐⭐⭐ CRITICAL: 날짜 포맷팅 전처리
watch(
  () => props.fetchedMainData,
  async (newData) => {
    if (!newData) return;
    
    await nextTick();
    
    newData.forEach((row: any) => {
      // 의뢰일자
      if (row.ASK_DT) {
        row.ASK_DT_FORMATTED = formatDate(row.ASK_DT, 'YYYYMMDD', 'YYYY-MM-DD');
      }
      
      // 요청일자
      if (row.REQ_DT) {
        row.REQ_DT_FORMATTED = formatDate(row.REQ_DT, 'YYYYMMDD', 'YYYY-MM-DD');
      }
      
      // 조달요청일자
      if (row.ASK_PRCR_COMPL_REQ_DT) {
        row.ASK_PRCR_COMPL_REQ_DT_FORMATTED = formatDate(
          row.ASK_PRCR_COMPL_REQ_DT,
          'YYYYMMDD',
          'YYYY-MM-DD'
        );
      }
      
      // 조달납기일자
      if (row.PRCR_DLVY_REQ_DT) {
        row.PRCR_DLVY_REQ_DT_FORMATTED = formatDate(
          row.PRCR_DLVY_REQ_DT,
          'YYYYMMDD',
          'YYYY-MM-DD'
        );
      }
      
      // 완료요구일자
      if (row.COMPL_REQ_DT) {
        row.COMPL_REQ_DT_FORMATTED = formatDate(
          row.COMPL_REQ_DT,
          'YYYYMMDD',
          'YYYY-MM-DD'
        );
      }
    });
  },
  { immediate: true }
);

// Expose
defineExpose({
  selectedRows,
});
</script>

<style scoped lang="scss">
.datatable-container {
  width: 100%;
  height: 100%;
}
</style>
```

## ✅ 구현 완료 체크리스트

### 가상 스크롤링
- [ ] scrollable 속성 추가
- [ ] scrollHeight="540px" (고정 높이)
- [ ] virtualScrollerOptions="{ itemSize: 46 }"
- [ ] itemSize 값 확인 (개발자 도구)

### 컬럼 정의
- [ ] selectionMode="multiple" 컬럼 추가
- [ ] frozen 컬럼 확인
- [ ] 모든 필드 매핑 확인
- [ ] headerClass, bodyClass 정렬 설정

### 날짜 포맷팅
- [ ] formatDate 유틸리티 함수 작성
- [ ] watch with nextTick 구현
- [ ] 모든 날짜 필드 전처리
- [ ] _FORMATTED 필드 사용

### GPU 가속 CSS
- [ ] will-change: background-color 추가
- [ ] contain: layout style 추가
- [ ] hover 선택자 최적화
- [ ] 헤더 정렬 순서 확인

### 테스트
- [ ] 1000개 이상 데이터 로딩 테스트
- [ ] 스크롤 성능 확인 (60 FPS)
- [ ] hover 성능 확인
- [ ] 날짜 포맷팅 확인

## 🐛 자주 발생하는 에러

### 1. 스크롤이 느림

**증상**: 대용량 데이터 스크롤 시 버벅임.

**원인**:
```vue
<!-- ❌ WRONG -->
<DataTable scrollHeight="flex">
```

**해결**:
```vue
<!-- ✅ CORRECT -->
<DataTable
  scrollHeight="540px"
  :virtualScrollerOptions="{ itemSize: 46 }"
>
```

### 2. 행 클릭 시 느림

**증상**: 행 선택 시 0.5초+ 지연.

**원인**: 템플릿 슬롯 포맷팅
```vue
<!-- ❌ WRONG -->
<Column field="ASK_DT">
  <template #body="{ data }">
    {{ formatDate(data.ASK_DT, ...) }}
  </template>
</Column>
```

**해결**:
```typescript
// ✅ CORRECT - watch 전처리
watch(() => props.fetchedMainData, async (newData) => {
  await nextTick();
  newData.forEach(row => {
    row.ASK_DT_FORMATTED = formatDate(row.ASK_DT, ...);
  });
});
```

```vue
<Column field="ASK_DT_FORMATTED" />
```

### 3. 헤더가 중앙 정렬되지 않음

**증상**: 특정 컬럼만 좌측 정렬.

**원인**: CSS 순서 문제
```scss
// ❌ WRONG - 순서가 반대
.left .p-datatable-column-header-content {
  justify-content: flex-start;
}

.p-datatable-column-header-content {
  justify-content: center;
}
```

**해결**:
```scss
// ✅ CORRECT - 전체 먼저, 특정 나중
.p-datatable-column-header-content {
  justify-content: center;
}

.left .p-datatable-column-header-content {
  justify-content: flex-start;
}
```

## 🎯 다음 단계

DataTable 구현이 완료되었다면 **[05_SumGrid_ProgressBar_구현.md](./05_SumGrid_ProgressBar_구현.md)**로 이동하세요.
