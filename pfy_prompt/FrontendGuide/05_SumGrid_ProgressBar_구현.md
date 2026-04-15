# 05. SumGrid / ProgressBar / ProgressList 구현

## ⚠️ CRITICAL: SumGrid 생성 조건

**SumGrid는 스펙에 진행상태별 집계 필터(예: 저장/의뢰/요청확정 등 상태별 건수를 클릭하여 필터링)가 명시된 경우에만 생성합니다.**

**다음 화면에서는 SumGrid를 생성하지 마세요:**
- 단순 목록 조회 화면 (검색 + 테이블만 있는 화면)
- CRUD 화면 (등록/수정/삭제만 있는 화면)
- 엑셀 업로드/다운로드 화면
- 진행상태 개념이 없는 화면

**다음 경우에만 SumGrid를 생성하세요:**
- 스펙에 "진행상태별 건수", "상태별 집계", "ProgressBar" 등이 명시된 경우
- 스펙에 상태 코드(예: 저장/의뢰/접수/완료 등)별 건수 표시 및 클릭 필터링 요구사항이 있는 경우

## 📋 이 단계의 목적

진행상태별 집계를 표시하고 필터링 기능을 제공하는 **SumGrid(ProgressBar) 컴포넌트** 구현 시 참고합니다.

- **신규 개발**: 진행상태별 집계가 스펙에 명시된 화면에서만 SumGrid/ProgressBar를 추가하며, 기존 패턴(예: spov010)을 따릅니다.
- **수정 개발**: 기존 화면의 SumGrid/ProgressBar 영역을 변경할 때 동일한 패턴을 유지합니다.
- **ProgressList**: 특수 상태를 분리해 표시할 때만 사용하며, 요구사항이나 요청이 있을 때만 추가합니다 (기본 생성 안 함).

## 📝 Step 1: 참고할 기존 화면 확인

### 1.1 참고 화면 확인

- **신규 시**: 유사한 기존 화면(같은 모듈/카테고리 또는 spov010 등)의 SumGrid/ProgressBar 구조와 동작을 확인합니다.
- **수정 시**: 변경 대상 화면의 기존 SumGrid/ProgressBar 구현을 확인합니다.

```bash
# 예: spov010 확인
# src/pages/sy/ds/spov010/components/spov010ProgressBar/ (또는 SumGrid)
```

### 1.2 핵심 패턴 추출

```vue
<!-- 예: spov010ProgressBar.vue -->
<script lang="ts" setup>
const searchParams = inject<Ref<Spov010SearchParams>>('searchParams')!;

const handleProgress = (next: string) => {
  // ⭐ CRITICAL: searchParams 직접 업데이트
  searchParams.value.prgStat = next === 'TOTAL' ? null : next;
  fetchOverviewDataList(searchParams.value);
};
</script>
```

**핵심**:
1. `searchParams` 직접 업데이트
2. `TOTAL` → `null` (조건 제거)
3. 특정 상태 → 해당 코드값

## 📝 Step 2: 기본 구조 생성

### 2.1 파일 생성 (신규 시)

**⚠️ screenId는 반드시 camelCase! 모두 소문자 금지!**

**신규 화면**에서 SumGrid를 추가할 때: `pages/[module]/[category]/[screenId]/components/[screenId]SumGrid/` 폴더를 만들고, `.vue`와 `.scss`를 생성합니다.

```bash
# 예시 1: 짧은 screenId
# pages/sy/ds/pmdp010/components/pmdp010SumGrid/
# PMDP010SumGrid.vue, PMDP010SumGrid.scss

# 예시 2: camelCase screenId (cpmsEduPondgLst)
# pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstSumGrid/
# CpmsEduPondgLstSumGrid.vue, CpmsEduPondgLstSumGrid.scss
```

**⚠️ 중요**:
- SCSS 파일은 필수입니다. SumGrid/ProgressBar 스타일을 포함합니다.
- 폴더명은 camelCase (예: `cpmsEduPondgLstSumGrid/`)
- Vue/SCSS 파일명은 PascalCase (예: `CpmsEduPondgLstSumGrid.vue`)

### 2.2 기본 템플릿

타입은 `api/pages/[module]/[category]/types.ts`에 정의된 해당 화면의 SearchParams·집계 응답 타입을 사용합니다.

```vue
<!-- 예: PMDP010SumGrid.vue -->
<template>
  <div class="sum-grid-container">
    <!-- 전체 건수 버튼 -->
    <div class="total-btn-box">
      <Button class="total-btn" @click="handleTotalClick">
        <span class="label">전체 건수</span>
        <strong class="count">{{ totalCount }}</strong>
      </Button>
    </div>
    
    <!-- 진행상태별 버튼 -->
    <div class="progress-items">
      <Button
        v-for="item in progressItems"
        :key="item.field"
        class="progress-btn"
        :class="{ active: searchParams.prg_stat === item.field }"
        @click="handleProgressClick(item.field)"
      >
        <span class="label">{{ item.label }}</span>
        <strong class="count">{{ item.count }}</strong>
      </Button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { inject, computed } from 'vue';
import type { Ref } from 'vue';
import Button from 'primevue/button';
import type { PMDP010SearchParams, PMDP010SelectDpAskStatSumResponse } from '@/api/pages/sy/ds/types';
// ↑ 해당 화면 타입: api/pages/[module]/[category]/types.ts

// Props
interface Props {
  fetchedSumData: PMDP010SelectDpAskStatSumResponse | null;
}

const props = defineProps<Props>();

// ⭐ inject searchParams
const searchParams = inject<Ref<PMDP010SearchParams>>('searchParams')!;
</script>

<style scoped lang="scss" src="./PMDP010SumGrid.scss"></style>
```

**⚠️ 중요**: `<style>` 태그에 SCSS 파일을 연결해야 ProgressBar 스타일이 적용됩니다!

## 📝 Step 3: 집계 데이터 처리

### 3.1 API 응답 구조 확인

집계 API 응답 타입은 `api/pages/[module]/[category]/types.ts`에 정의합니다.

```typescript
// api/pages/sy/ds/types.ts (예)
export interface PMDP010SelectDpAskStatSumResponse {
  dsOutput: {
    BUSN_SC?: string;
    STAT_TOT?: number;
    STAT_SAVE?: number;
    STAT_ASK?: number;
    STAT_REQ?: number;
    STAT_CANC?: number;
  }[];
}
```

### 3.2 전체 건수 계산

```typescript
const totalCount = computed(() => {
  if (!props.fetchedSumData?.dsOutput?.[0]) return 0;
  return props.fetchedSumData.dsOutput[0].STAT_TOT || 0;
});
```

### 3.3 진행상태별 아이템 구성

```typescript
const progressItems = computed(() => {
  if (!props.fetchedSumData?.dsOutput?.[0]) {
    return [
      { field: 'S01', label: '저장', count: 0 },
      { field: 'S02', label: '의뢰', count: 0 },
      { field: 'S03', label: '요청확정', count: 0 },
      { field: 'S04', label: '요청철회', count: 0 },
    ];
  }
  
  const data = props.fetchedSumData.dsOutput[0];
  
  return [
    { field: 'S01', label: '저장', count: data.STAT_SAVE || 0 },
    { field: 'S02', label: '의뢰', count: data.STAT_ASK || 0 },
    { field: 'S03', label: '요청확정', count: data.STAT_REQ || 0 },
    { field: 'S04', label: '요청철회', count: data.STAT_CANC || 0 },
  ];
});
```

## 📝 Step 4: 클릭 이벤트 구현 (CRITICAL!)

### 4.1 전체 건수 버튼

```typescript
// ⭐⭐⭐ CRITICAL: 기존 패턴
const handleTotalClick = () => {
  // ⚠️ DO: null 할당 (빈 문자열 아님!)
  searchParams.value.prg_stat = null;
};
```

#### ⚠️ DO: `null` 사용

백엔드가 대문자 파라미터·조건부 쿼리를 사용하는 경우, **전체 조회** 시 해당 조건을 비우려면 `null`을 사용합니다.

```typescript
// ✅ CORRECT - 전체 조회 시 조건 제외
searchParams.value.prg_stat = null;

// API 레이어에서: null/undefined/빈 문자열이면 파라미터에 포함하지 않음
// → 백엔드에서 해당 조건이 적용되지 않음 (전체 조회)
```

#### ⚠️ DON'T: 빈 문자열 사용

```typescript
// ❌ WRONG - 빈 문자열이 전달되면 백엔드에서 조건 추가될 수 있음
searchParams.value.prg_stat = '';

// API에서 빈 값이 넘어가면 WHERE PRG_STAT = '' 등으로 잘못된 결과 발생 가능
```

### 4.2 진행상태별 버튼

```typescript
const handleProgressClick = (field: string) => {
  // ⭐ CRITICAL: searchParams 직접 업데이트
  searchParams.value.prg_stat = field;
};
```

#### ⚠️ DO: 기존 패턴 (searchParams만 갱신)

```typescript
// ✅ CORRECT - 간단하고 명확
const handleProgressClick = (field: string) => {
  searchParams.value.prg_stat = field;
};
```

**이유**:
1. `searchParams` 업데이트 → 자동으로 watch 트리거
2. SearchForm watch → SelectBox 동기화
3. 조회 버튼 클릭 → 최신 searchParams 사용

#### ⚠️ DON'T: 복잡한 ref 체인

```typescript
// ❌ WRONG - 과거 방식, 동작하지 않음
const handleProgressClick = (field: string) => {
  // 1. searchFormRef inject (불필요)
  const searchFormRef = inject('searchFormRef');
  
  // 2. SelectBox 직접 업데이트 시도 (실패)
  searchFormRef.value?.form.setFieldValue('prg_stat', field);
  
  // 3. searchParams도 업데이트 (중복)
  searchParams.value.prg_stat = field;
};
```

**문제점**:
- `searchFormRef`가 `undefined`일 수 있음
- Ref 접근 경로 복잡
- 중복 코드
- watch 패턴 무시

### 4.3 동작 흐름 정리

```
1. 사용자가 "저장" 버튼 클릭
   ↓
2. handleProgressClick('S01') 실행
   ↓
3. searchParams.value.prg_stat = 'S01'
   ↓
4. SearchForm watch 감지
   watch(() => searchParams.value?.prg_stat, ...)
   ↓
5. setFieldValue('prg_stat', 'S01')
   ↓
6. SelectBox 값 업데이트
   ↓
7. 사용자가 조회 버튼 클릭
   ↓
8. API 호출 (searchParams.prg_stat === 'S01')
```

## 📝 Step 5: CSS 스타일링

### 5.1 기존 화면 패턴 참고

기존 SumGrid/ProgressBar 스타일(예: spov010, pmdp010)과 동일한 톤앤매너를 유지합니다.

```scss
// [screenId]SumGrid.scss (예: pmdp010SumGrid.scss)
.sum-grid-container {
  width: 100%;
  padding: 15px 95px 15px 32px;
  background-color: var(--bg-2);
  border-radius: 8px;
  display: flex;
  gap: 90px;
  align-items: center;
  margin-bottom: 16px;
  
  // 전체 건수 버튼
  .total-btn-box {
    flex-shrink: 0;
    
    .total-btn {
      width: 230px;
      padding: 10px 24px;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 4px;
      background-color: var(--bg-1);
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
      
      .label {
        font-size: 14px;
        color: var(--text-secondary);
        font-weight: 600;
      }
      
      .count {
        font-size: 24px;
        color: var(--text-primary);
        font-weight: 700;
      }
      
      &:hover {
        background-color: var(--primary-color);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        
        .label,
        .count {
          color: white;
        }
      }
      
      &:active {
        transform: translateY(0);
      }
    }
  }
  
  // 진행상태별 버튼들
  .progress-items {
    flex: 1;
    display: flex;
    gap: 24px;
    
    .progress-btn {
      flex: 1;
      padding: 10px 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      background-color: var(--bg-1);
      border: 2px solid transparent;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
      
      .label {
        font-size: 13px;
        color: var(--text-secondary);
        font-weight: 600;
      }
      
      .count {
        font-size: 20px;
        color: var(--text-primary);
        font-weight: 700;
      }
      
      // ⭐ hover 효과
      &:hover {
        background-color: var(--primary-50);
        border-color: var(--primary-color);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        
        .label {
          color: var(--primary-color);
        }
      }
      
      // ⭐ active 상태 (선택된 버튼)
      &.active {
        background-color: var(--primary-color);
        border-color: var(--primary-color);
        
        .label,
        .count {
          color: white;
        }
      }
      
      &:active {
        transform: translateY(0);
      }
    }
  }
}
```

### 5.2 CSS 변수 사용

```scss
// 색상은 CSS 변수로 관리
--bg-1: #ffffff;
--bg-2: #f8f9fa;
--text-primary: #212529;
--text-secondary: #6c757d;
--primary-color: #0d6efd;
--primary-50: rgba(13, 110, 253, 0.1);
```

**장점**:
- 테마 변경 용이
- 다크 모드 지원 가능
- 일관된 색상 관리

### 5.3 애니메이션 효과

```scss
.progress-btn {
  transition: all 0.2s;  // ⭐ 부드러운 전환
  
  &:hover {
    transform: translateY(-2px);      // ⭐ 위로 살짝 이동
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);  // ⭐ 그림자 추가
  }
  
  &:active {
    transform: translateY(0);  // ⭐ 클릭 시 원위치
  }
}
```

## 📝 Step 6: 완성 코드

```vue
<template>
  <div class="sum-grid-container">
    <!-- 전체 건수 버튼 -->
    <div class="total-btn-box">
      <Button
        class="total-btn"
        :class="{ active: searchParams.prg_stat === null }"
        @click="handleTotalClick"
      >
        <span class="label">전체 건수</span>
        <strong class="count">{{ totalCount }}</strong>
      </Button>
    </div>
    
    <!-- 진행상태별 버튼 -->
    <div class="progress-items">
      <Button
        v-for="item in progressItems"
        :key="item.field"
        class="progress-btn"
        :class="{ active: searchParams.prg_stat === item.field }"
        @click="handleProgressClick(item.field)"
      >
        <span class="label">{{ item.label }}</span>
        <strong class="count">{{ item.count }}</strong>
      </Button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { inject, computed } from 'vue';
import type { Ref } from 'vue';
import Button from 'primevue/button';
import type {
  PMDP010SearchParams,
  PMDP010SelectDpAskStatSumResponse,
} from '@/api/pages/sy/ds/types';

// Props
interface Props {
  fetchedSumData: PMDP010SelectDpAskStatSumResponse | null;
}

const props = defineProps<Props>();

// ⭐ inject searchParams
const searchParams = inject<Ref<PMDP010SearchParams>>('searchParams')!;

// 전체 건수
const totalCount = computed(() => {
  if (!props.fetchedSumData?.dsOutput?.[0]) return 0;
  return props.fetchedSumData.dsOutput[0].STAT_TOT || 0;
});

// 진행상태별 아이템
const progressItems = computed(() => {
  if (!props.fetchedSumData?.dsOutput?.[0]) {
    return [
      { field: 'S01', label: '저장', count: 0 },
      { field: 'S02', label: '의뢰', count: 0 },
      { field: 'S03', label: '요청확정', count: 0 },
      { field: 'S04', label: '요청철회', count: 0 },
    ];
  }
  
  const data = props.fetchedSumData.dsOutput[0];
  
  return [
    { field: 'S01', label: '저장', count: data.STAT_SAVE || 0 },
    { field: 'S02', label: '의뢰', count: data.STAT_ASK || 0 },
    { field: 'S03', label: '요청확정', count: data.STAT_REQ || 0 },
    { field: 'S04', label: '요청철회', count: data.STAT_CANC || 0 },
  ];
});

// ⭐⭐⭐ CRITICAL: 기존 패턴 (searchParams만 갱신)
const handleTotalClick = () => {
  searchParams.value.prg_stat = null;
};

const handleProgressClick = (field: string) => {
  searchParams.value.prg_stat = field;
};
</script>

<style scoped lang="scss">
@import './pmdp010SumGrid.scss';
</style>
```

## ✅ 구현 완료 체크리스트

### 기본 구조
- [ ] searchParams inject
- [ ] totalCount computed
- [ ] progressItems computed
- [ ] 전체 건수 버튼
- [ ] 진행상태별 버튼들

### 클릭 이벤트
- [ ] handleTotalClick: searchParams.value.prg_stat = null
- [ ] handleProgressClick: searchParams.value.prg_stat = field
- [ ] 기존 패턴 준수 (복잡한 ref 체인 사용 금지)

### CSS 스타일링
- [ ] 기존 화면(예: spov010) 스타일·동작 참고
- [ ] hover 효과 추가
- [ ] active 클래스 추가
- [ ] 애니메이션 효과 추가
- [ ] CSS 변수 사용

### 테스트
- [ ] 전체 건수 버튼 클릭 → prg_stat = null
- [ ] 진행상태 버튼 클릭 → prg_stat = 해당 코드
- [ ] SelectBox 동기화 확인
- [ ] 조회 버튼 클릭 → 필터링 작동 확인

## 🐛 자주 발생하는 에러

### 1. 전체 건수 버튼 클릭 시 조회 안 됨

**증상**: 전체 버튼 클릭 시 데이터가 조회되지 않음.

**원인**:
```typescript
// ❌ WRONG - 빈 문자열
searchParams.value.prg_stat = '';
```

**해결**:
```typescript
// ✅ CORRECT - null
searchParams.value.prg_stat = null;
```

### 2. SelectBox가 업데이트되지 않음

**증상**: 진행상태 버튼 클릭 시 SelectBox 값이 변하지 않음.

**원인**: SearchForm의 watch 조건 문제
```typescript
// ❌ WRONG - SearchForm.vue
if (newVal) {
  searchFormRef.value.form.setFieldValue('prg_stat', newVal);
}
```

**해결**:
```typescript
// ✅ CORRECT - SearchForm.vue
if (newVal !== undefined && searchFormRef.value?.form) {
  searchFormRef.value.form.setFieldValue('prg_stat', newVal ?? '');
}
```

### 3. 복잡한 ref 체인 사용

**증상**: `searchFormRef.value.value.form is undefined`

**원인**:
```typescript
// ❌ WRONG - 불필요한 복잡성
const searchFormRef = inject('searchFormRef');
searchFormRef.value?.form.setFieldValue('prg_stat', field);
searchParams.value.prg_stat = field;
```

**해결**:
```typescript
// ✅ CORRECT - 기존 패턴
searchParams.value.prg_stat = field;
// watch가 알아서 SelectBox 동기화
```

---

## 📝 Step 8: ProgressList 구현 (선택사항 - 요청 시에만)

**신규 화면에서는 기본으로 만들지 않습니다.** 요구사항이나 사용자 요청이 있을 때만 ProgressList를 추가합니다.

### 8.1 ProgressList가 무엇인가?

**ProgressList**는 특수한 상태 항목들을 SumGrid에서 분리하여 별도로 표시하는 컴포넌트입니다.

**사용 예시**:
- SPOV010: 특수 진행상태 항목 분리
- PMDP020: 요청미확정(S03), 취소요청(Q01), 취소승인(Q02) 분리
- PMDP030: 취소요청(Q01), 취소승인(Q02) 분리

**주요 특징**:
- 세로 리스트 형태 (`<ul><li>` 구조)
- 총알 모양 bullet point (::before 사용)
- 빨간색 강조 (`.has-value` 클래스)
- 고정 너비 230px 버튼
- 고정 높이 122px 컨테이너
- SPOV010 스타일 패턴 기반

### 8.2 언제 생성하는가?

**⚠️ 중요**: ProgressList는 **기본적으로 생성하지 않습니다**. 다음 경우에만 생성:

```typescript
// ✅ 사용자가 명시적으로 요청할 때만
"SPOV010에 Spov010ProgressList 이거있지? 이 부분에 들어가는 거를 PMDP020의 '요청미확정', '취소요청', '취소승인' 이 세개를 Spov010ProgressList 처럼 나오게끔 해주고 싶어"

"ProgressList 추가해줘"
"취소 관련 상태를 분리해서 보여줘"
"SPOV010 패턴 적용해줘"
```

**❌ 자동으로 생성하지 말 것**:
- 화면 구현 시 기본으로 만들지 않음
- "ProgressList가 필요하신가요?" 같은 질문 하지 않음
- 모든 상태 항목에 대해 만들지 않음

### 8.3 파일 생성

```bash
# 사용자가 요청했을 때만 생성
mkdir -p src/pages/sy/ds/pmdp020/components/pmdp020ProgressList
touch src/pages/sy/ds/pmdp020/components/pmdp020ProgressList/PMDP020ProgressList.vue
touch src/pages/sy/ds/pmdp020/components/pmdp020ProgressList/PMDP020ProgressList.scss
```

### 8.4 기본 템플릿 (SPOV010 패턴)

```vue
<!-- PMDP020ProgressList.vue -->
<template>
  <div class="progress-list-container">
    <ul class="progress-list">
      <li>
        <button
          class="progress-btn"
          @click="handleProgress('S03')"
        >
          <span class="progress-btn-text">요청미확정</span>
          <span
            class="progress-btn-count"
            :class="{ 'has-value': sumData.S03 > 0 }"
          >
            {{ sumData.S03 }}
          </span>
        </button>
      </li>
      <li>
        <button
          class="progress-btn"
          @click="handleProgress('Q01')"
        >
          <span class="progress-btn-text">취소요청</span>
          <span
            class="progress-btn-count"
            :class="{ 'has-value': sumData.Q01 > 0 }"
          >
            {{ sumData.Q01 }}
          </span>
        </button>
      </li>
      <li>
        <button
          class="progress-btn"
          @click="handleProgress('Q02')"
        >
          <span class="progress-btn-text">취소승인</span>
          <span
            class="progress-btn-count"
            :class="{ 'has-value': sumData.Q02 > 0 }"
          >
            {{ sumData.Q02 }}
          </span>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue';

const fetchedSumData = inject('fetchedSumData') as any;
const searchParams = inject('searchParams') as any;
const fetchData = inject('fetchData') as Function;

const sumData = computed(() => {
  if (fetchedSumData.value?.dsOutput?.[0]) {
    return fetchedSumData.value.dsOutput[0];
  }
  return { S03: 0, Q01: 0, Q02: 0 };
});

const handleProgress = (field: string) => {
  // S03는 PRG_STAT, Q01/Q02는 CANC_STAT 사용
  if (field === 'S03') {
    searchParams.value = {
      ...searchParams.value,
      prg_stat: field,
      canc_stat: 'Q00', // 정상
    };
  } else {
    searchParams.value = {
      ...searchParams.value,
      prg_stat: '', // 전체
      canc_stat: field,
    };
  }
  
  fetchData(searchParams.value);
};
</script>

<style scoped lang="scss" src="./PMDP020ProgressList.scss"></style>
```

### 8.5 스타일링 (SPOV010 패턴)

```scss
// PMDP020ProgressList.scss
.progress-list-container {
  background-color: var(--bg-2);
  padding: 14px 24px;
  height: 122px;
  border-radius: 8px;
  display: flex;
  align-items: center;
}

.progress-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;

  > li {
    display: flex;
    align-items: center;
    gap: 12px;

    &::before {
      content: '';
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--button-outlined-color);
      flex-shrink: 0;
    }
  }
}

.progress-btn {
  width: 230px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  background-color: transparent;
  border: 1px solid var(--button-outlined-color);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background-color: var(--button-outlined-hover-bg);
  }

  .progress-btn-text {
    font-size: 14px;
    color: var(--text-color);
  }

  .progress-btn-count {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-color);

    &.has-value {
      color: red;
    }
  }
}
```

### 8.6 SumGrid에서 항목 제거

ProgressList를 생성한 후에는 **반드시** SumGrid의 progressItems에서 해당 항목들을 제거해야 합니다.

```typescript
// PMDP020SumGrid.vue
// ❌ BEFORE - 7개 항목
const progressItems = [
  { field: 'S02', label: '의뢰', severity: 'primary' },
  { field: 'A01', label: '저장', severity: 'secondary' },
  { field: 'A02', label: '요청', severity: 'info' },
  { field: 'B01', label: '접수', severity: 'success' },
  { field: 'S03', label: '요청미확정', severity: 'warning' },  // ← 제거
  { field: 'Q01', label: '취소요청', severity: 'danger' },     // ← 제거
  { field: 'Q02', label: '취소승인', severity: 'secondary' },  // ← 제거
];

// ✅ AFTER - 4개 항목 (ProgressList로 이동한 3개 제거)
const progressItems = [
  { field: 'S02', label: '의뢰', severity: 'primary' },
  { field: 'A01', label: '저장', severity: 'secondary' },
  { field: 'A02', label: '요청', severity: 'info' },
  { field: 'B01', label: '접수', severity: 'success' },
];
```

### 8.7 index.vue에 ProgressList 추가

```vue
<!-- index.vue -->
<script lang="ts" setup>
import PMDP020ProgressList from '@/pages/sy/ds/pmdp020/components/pmdp020ProgressList/PMDP020ProgressList.vue';
// ... other imports
</script>

<template>
  <div class="main-content-container">
    <ContentHeader menuId="PMDP020" />
    <PMDP020SearchForm />
    <div class="summary-section">
      <PMDP020SumGrid />
      <PMDP020ProgressList />
    </div>
    <PMDP020DataTable />
  </div>
</template>
```

### 8.8 레이아웃 스타일링

```scss
// pmdp020.scss
.summary-section {
  display: flex;
  gap: 8px;  // SumGrid와 ProgressList 사이 간격
  margin-bottom: 1rem;
}
```

### 8.9 예제 - PMDP030 (2개 항목만)

PMDP030처럼 더 적은 항목을 가진 ProgressList:

```vue
<!-- PMDP030ProgressList.vue - 취소요청, 취소승인만 -->
<template>
  <div class="progress-list-container">
    <ul class="progress-list">
      <li>
        <button class="progress-btn" @click="handleProgress('Q01')">
          <span class="progress-btn-text">취소요청</span>
          <span
            class="progress-btn-count"
            :class="{ 'has-value': sumData.Q01 > 0 }"
          >
            {{ sumData.Q01 }}
          </span>
        </button>
      </li>
      <li>
        <button class="progress-btn" @click="handleProgress('Q02')">
          <span class="progress-btn-text">취소승인</span>
          <span
            class="progress-btn-count"
            :class="{ 'has-value': sumData.Q02 > 0 }"
          >
            {{ sumData.Q02 }}
          </span>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
// Q01, Q02만 사용하는 로직
const sumData = computed(() => {
  return fetchedSumData.value?.dsOutput?.[0] || { Q01: 0, Q02: 0 };
});

const handleProgress = (field: string) => {
  searchParams.value = {
    ...searchParams.value,
    prg_stat: '',
    canc_stat: field,
  };
  fetchData(searchParams.value);
};
</script>
```

### 8.10 ProgressList 체크리스트

ProgressList를 생성할 때 확인할 사항:

- [ ] 사용자가 명시적으로 요청했는가?
- [ ] SPOV010 패턴을 참고했는가?
- [ ] Template-first 구조로 작성했는가?
- [ ] `progress-list-container` 클래스를 사용했는가?
- [ ] `<ul><li>` 구조로 작성했는가?
- [ ] `li::before` 로 bullet point를 추가했는가?
- [ ] 버튼 너비 230px로 설정했는가?
- [ ] 컨테이너 높이 122px로 설정했는가?
- [ ] `.has-value` 클래스로 빨간색 강조했는가?
- [ ] SumGrid에서 해당 항목들을 제거했는가?
- [ ] index.vue에 ProgressList 컴포넌트를 추가했는가?
- [ ] summary-section에 flex 레이아웃을 적용했는가?
- [ ] gap: 8px를 설정했는가?
- [ ] handleProgress 로직이 올바른가? (PRG_STAT vs CANC_STAT)

---

## 🎯 다음 단계

SumGrid(및 선택적 ProgressList) 구현이 완료되었다면 **[06_API_백엔드_연동.md](./06_API_백엔드_연동.md)**로 이동하세요. 신규/수정 모두 API·타입은 `api/pages/[module]/[category]/` 규칙을 따릅니다.
