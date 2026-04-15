# 03. SearchForm 구현

## 📋 이 단계의 목적

검색 조건을 입력받는 **SearchForm 컴포넌트**를 구현합니다.

## 📝 Step 1: 기본 구조 생성

### 1.1 파일 생성

**⚠️ screenId는 반드시 camelCase! 모두 소문자 금지!**

```bash
# 예시 1: 짧은 screenId
mkdir -p src/pages/sy/ds/pmdp010/components/pmdp010SearchForm
touch src/pages/sy/ds/pmdp010/components/pmdp010SearchForm/PMDP010SearchForm.vue
touch src/pages/sy/ds/pmdp010/components/pmdp010SearchForm/PMDP010SearchForm.scss

# 예시 2: camelCase screenId (cpmsEduPondgEdit)
mkdir -p src/pages/edu/pondg/cpmsEduPondgEdit/components/cpmsEduPondgEditSearchForm
touch .../cpmsEduPondgEditSearchForm/CpmsEduPondgEditSearchForm.vue
touch .../cpmsEduPondgEditSearchForm/CpmsEduPondgEditSearchForm.scss
```

**⚠️ 중요**:
- SCSS 파일은 필수입니다! 컴포넌트별 스타일을 분리하여 관리합니다.
- 폴더명은 camelCase (예: `cpmsEduPondgEditSearchForm/`)
- Vue/SCSS 파일명은 PascalCase (예: `CpmsEduPondgEditSearchForm.vue`)

### 1.2 Component Import Patterns (중요!)

**Rule**: `index.ts`가 있는지 확인하여 import 방식을 결정합니다.

```typescript
// ✅ CORRECT - index.ts가 있는 컴포넌트 (Destructuring)
import { Button } from '@/components/common/button';
import { DatePicker } from '@/components/common/datePicker';
import { 
  SearchForm, 
  SearchFormContent, 
  SearchFormField, 
  SearchFormRow 
} from '@/components/common/searchForm';

// ✅ CORRECT - index.ts가 없는 컴포넌트 (Direct import)
import SearchFormLabel from '@/components/common/searchForm/SearchFormLabel.vue';
import InputText from '@/components/common/inputText/InputText.vue';
import Select from '@/components/common/select/Select.vue';

// ❌ WRONG - PrimeVue 직접 import
import Button from 'primevue/button';
import Calendar from 'primevue/calendar';
```

**확인 방법**:
1. `tomms-lite-front/src/components/common/[componentName]/index.ts` 존재 여부 확인
2. 존재하면 → Destructuring import 사용
3. 없으면 → Direct `.vue` import 사용
4. 참조 화면 (spov010) 패턴 확인

### 1.3 기본 템플릿

**⚠️ 주의**: SearchForm은 반드시 별도 파일로 분리! index.vue에 인라인으로 넣지 마세요!

**⚠️ CRITICAL: SearchFormRow로 필드를 감싸야 가로 배치됩니다! SearchFormRow 없이 SearchFormField를 직접 나열하면 세로 1열로 쌓입니다!**

```vue
<!-- CpmsEduPondgEditSearchForm.vue (또는 PMDP010SearchForm.vue) -->
<template>
  <SearchForm
    ref="searchFormRef"
    :initialValues="initialValues"
    @submit="handleSubmit"
    @reset="handleReset"
  >
    <!-- ⭐ CRITICAL: SearchFormRow로 감싸야 가로 배치! -->
    <SearchFormRow>
      <SearchFormField v-slot="{ props }" name="field1">
        <SearchFormLabel>라벨1</SearchFormLabel>
        <SearchFormContent>
          <InputText v-bind="props" placeholder="입력" />
        </SearchFormContent>
      </SearchFormField>

      <SearchFormField v-slot="{ props }" name="field2">
        <SearchFormLabel>라벨2</SearchFormLabel>
        <SearchFormContent>
          <Select v-bind="props" :options="options" optionLabel="name" optionValue="value" />
        </SearchFormContent>
      </SearchFormField>

      <SearchFormField v-slot="{ props }" name="field3">
        <SearchFormLabel>라벨3</SearchFormLabel>
        <SearchFormContent>
          <InputText v-bind="props" placeholder="입력" />
        </SearchFormContent>
      </SearchFormField>
    </SearchFormRow>

    <!-- 두 번째 행 -->
    <SearchFormRow>
      <SearchFormField v-slot="{ props }" name="field4">
        <SearchFormLabel>라벨4</SearchFormLabel>
        <SearchFormContent>
          <InputText v-bind="props" placeholder="입력" />
        </SearchFormContent>
      </SearchFormField>

      <!-- ⭐ SearchFormFieldGroup: 관련 필드 묶기 (예: 날짜유형 + 날짜범위) -->
      <SearchFormFieldGroup>
        <SearchFormField v-slot="{ props }" name="dateType">
          <SearchFormLabel>조회기간</SearchFormLabel>
          <SearchFormContent>
            <Select v-bind="props" :options="dateTypeOptions" optionLabel="name" optionValue="value" />
          </SearchFormContent>
        </SearchFormField>
        <SearchFormField v-slot="{ props }" name="dateRange">
          <SearchFormContent>
            <DatePicker v-bind="props" selectionMode="range" showIcon style="min-width: 255px" />
          </SearchFormContent>
        </SearchFormField>
      </SearchFormFieldGroup>
    </SearchFormRow>
  </SearchForm>
</template>

<script lang="ts" setup>
import { ref, computed, inject, watch, onMounted } from 'vue';
import type { Ref } from 'vue';

import { 
  SearchForm, 
  SearchFormContent, 
  SearchFormField, 
  SearchFormFieldGroup,
  SearchFormRow 
} from '@/components/common/searchForm';
import SearchFormLabel from '@/components/common/searchForm/SearchFormLabel.vue';
import { Button } from '@/components/common/button';
import { DatePicker } from '@/components/common/datePicker';
import InputText from '@/components/common/inputText/InputText.vue';
import Select from '@/components/common/select/Select.vue';

// ⭐ 타입은 api/pages/[module]/[category]/types.ts에서 import
import type { CpmsEduPondgEditSearchParams } from '@/api/pages/edu/pondg/types';

interface Emits {
  (e: 'search'): void;
}
const emit = defineEmits<Emits>();

const searchParams = inject<Ref<CpmsEduPondgEditSearchParams>>('searchParams')!;
const searchFormRef = ref();

const initialValues = { /* 초기값 */ };

const handleSubmit = () => {
  emit('search');
};

const handleReset = () => {
  // 초기화 로직
};

defineExpose({
  searchFormRef,
});
</script>

<!-- ⚠️ SCSS 파일 연결 필수! 파일명은 PascalCase -->
<style scoped lang="scss" src="./CpmsEduPondgEditSearchForm.scss"></style>
```

**⚠️ 중요**:
- `<style>` 태그에 SCSS 파일을 연결해야 합니다!
- SCSS 파일명은 Vue 파일명과 동일하게 PascalCase (예: `CpmsEduPondgEditSearchForm.scss`)

### 1.4 레이아웃 규칙 (CRITICAL!)

**⚠️ SearchFormRow를 사용하지 않으면 필드가 세로로 쌓입니다!**

```
❌ WRONG (세로 배치 — SearchFormRow 없음):
┌──────────────────────────────────────────────┐
│ 라벨1  [입력]                                 │
│ 라벨2  [입력]                                 │
│ 라벨3  [입력]                                 │
│ 라벨4  [입력]                      [초기화][조회]│
└──────────────────────────────────────────────┘

✅ CORRECT (가로 배치 — SearchFormRow 사용):
┌──────────────────────────────────────────────┐
│ 라벨1  [입력]  라벨2  [입력]  라벨3  [입력]     │
│ 라벨4  [입력]  라벨5  [입력]        [초기화][조회]│
└──────────────────────────────────────────────┘
```

**규칙**:
1. 한 `SearchFormRow`에 2~3개 `SearchFormField`를 배치 → 가로 배치
2. 관련 필드(예: 날짜유형 + 날짜범위)는 `SearchFormFieldGroup`으로 묶기
3. 전체 필드 수가 4개 이하면 `SearchFormRow` 1개, 5개 이상이면 2개 이상으로 분할

## 📝 Step 2: 공통코드 로딩

### 2.1 Nexacro 패턴 분석

```javascript
// PMDP010.xfdl
this.gfnGetCodeComboSync([
  [this.divCond.form.cbPRG_STAT, "MNPS010Query.StatComboIn|A", customParam],
  [this.divCond.form.cbCANC_STAT, "COM_PBL_0005", "P_CODE_CD='C'"],
]);
```

### 2.2 Vue로 변환

```typescript
import { useCommonCodeStore } from '@/stores/commonCode';
import { onMounted } from 'vue';

const commonCodeStore = useCommonCodeStore();

onMounted(async () => {
  await commonCodeStore.loadMulti([
    {
      QueryId: 'MNPS010Query.StatComboIn',
      customParam: 'BUSN_SC_IN=A1 PROG_ID=PMDP010',
    },
    {
      QueryId: 'COM_PBL_0005',
      whereClause: "P_CODE_CD='C'",
    },
  ]);
});
```

### 2.3 옵션 사용

```typescript
const prgStatOptions = computed(() => 
  commonCodeStore.options('MNPS010Query.StatComboIn', true, '전체', 'ALL')
);

const cancStatOptions = computed(() => 
  commonCodeStore.options('COM_PBL_0005', true, '전체', 'ALL', "P_CODE_CD='C'")
);
```

## 📝 Step 3: SearchFormConfig 구성

### 3.1 기본 필드 추가

```typescript
const searchFormConfig = computed<SearchFormConfig>(() => ({
  groups: [
    {
      label: '검색조건',
      fields: [
        {
          name: 'searchDtType',
          label: '조회일자',
          component: 'RadioButtonGroup',
          props: {
            options: [
              { label: '의뢰일자', value: 'askDt' },
              { label: '요청일자', value: 'reqDt' },
            ],
            defaultValue: 'askDt',
          },
        },
        {
          name: 'searchDt',
          label: ' ',
          component: 'Calendar',
          props: {
            selectionMode: 'range',
            placeholder: '날짜 선택',
          },
        },
        {
          name: 'prg_stat',
          label: '진행상태',
          component: 'Select',
          props: {
            options: prgStatOptions.value,
            placeholder: '전체',
            showClear: true,
          },
        },
        {
          name: 'canc_stat',
          label: '철회상태',
          component: 'Select',
          props: {
            options: cancStatOptions.value,
            placeholder: '전체',
            showClear: true,
          },
        },
        {
          name: 'cont_no',
          label: '계약번호',
          component: 'InputText',
          props: {
            placeholder: '계약번호 입력',
          },
        },
        // ... 추가 필드
      ],
    },
  ],
}));
```

### 3.2 필드 타입별 예시

#### A. Select (Dropdown)

```typescript
{
  name: 'prg_stat',
  label: '진행상태',
  component: 'Select',
  props: {
    options: prgStatOptions.value,
    placeholder: '전체',
    showClear: true,      // X 버튼 표시
    filter: false,         // 검색 기능 비활성화
  },
}
```

#### B. InputText

```typescript
{
  name: 'cont_no',
  label: '계약번호',
  component: 'InputText',
  props: {
    placeholder: '계약번호 입력',
    maxlength: 20,
  },
}
```

#### C. Calendar (날짜 범위)

```typescript
{
  name: 'searchDt',
  label: '조회기간',
  component: 'Calendar',
  props: {
    selectionMode: 'range',
    dateFormat: 'yy-mm-dd',
    placeholder: '날짜 선택',
    showButtonBar: true,
  },
}
```

#### D. RadioButtonGroup

```typescript
{
  name: 'searchDtType',
  label: '조회일자',
  component: 'RadioButtonGroup',
  props: {
    options: [
      { label: '의뢰일자', value: 'askDt' },
      { label: '요청일자', value: 'reqDt' },
    ],
    defaultValue: 'askDt',
  },
}
```

## 📝 Step 4: watch 패턴 구현 (CRITICAL!)

### 4.1 tomms-lite-front 패턴

```typescript
// ⭐⭐⭐ CRITICAL: SelectBox 동기화
watch(
  () => searchParams.value?.prg_stat,
  (newVal) => {
    // ⚠️ DO: newVal !== undefined 조건
    if (newVal !== undefined && searchFormRef.value?.form) {
      // ⚠️ DO: .value.form.setFieldValue
      searchFormRef.value.form.setFieldValue('prg_stat', newVal ?? '');
    }
  }
);

watch(
  () => searchParams.value?.canc_stat,
  (newVal) => {
    if (newVal !== undefined && searchFormRef.value?.form) {
      searchFormRef.value.form.setFieldValue('canc_stat', newVal ?? '');
    }
  }
);
```

### 4.2 watch 조건 상세 설명

#### ⚠️ DO: `newVal !== undefined`

```typescript
// ✅ CORRECT - undefined만 제외
if (newVal !== undefined && searchFormRef.value?.form) {
  searchFormRef.value.form.setFieldValue('prg_stat', newVal ?? '');
}
```

#### ⚠️ DON'T: `if (newVal)`

```typescript
// ❌ WRONG - null과 빈 문자열도 제외됨
if (newVal && searchFormRef.value?.form) {
  searchFormRef.value.form.setFieldValue('prg_stat', newVal);
}
```

**문제점**:
- `newVal = null` → `if (null)` → false → 업데이트 안 됨
- `newVal = ''` → `if ('')` → false → 업데이트 안 됨
- `newVal = 'S01'` → `if ('S01')` → true → 업데이트 됨

**결과**: 전체 보기 버튼(null) 클릭 시 SelectBox가 업데이트되지 않음!

### 4.3 Ref 접근 경로 상세 설명

#### ⚠️ DO: `searchFormRef.value.form.setFieldValue`

```typescript
// ✅ CORRECT
searchFormRef.value.form.setFieldValue('prg_stat', newVal ?? '');
```

#### ⚠️ DON'T: 추가 `.value`

```typescript
// ❌ WRONG - .value.value는 존재하지 않음
searchFormRef.value.value.form.setFieldValue('prg_stat', newVal);

// ❌ WRONG - .form.value도 틀림
searchFormRef.value.form.value.setFieldValue('prg_stat', newVal);
```

**이유**:

1. **SearchForm 컴포넌트의 defineExpose**:
   ```typescript
   // SearchForm.vue
   defineExpose({
     searchFormRef,  // ← 이미 ref 자체를 expose
   });
   ```

2. **Vue의 자동 unwrap**:
   ```typescript
   // Parent에서 접근
   const searchFormRef = ref();  // ← ref 생성
   
   // Vue가 자동으로 unwrap
   searchFormRef.value  // → expose된 객체
   searchFormRef.value.searchFormRef  // → 내부 ref
   searchFormRef.value.form  // → 실제 form 인스턴스
   ```

### 4.4 실제 동작 흐름

```
1. SumGrid에서 버튼 클릭
   → searchParams.value.prg_stat = 'S01'

2. watch 감지
   → watch(() => searchParams.value?.prg_stat, ...)

3. 조건 확인
   → newVal = 'S01'
   → newVal !== undefined → true
   → searchFormRef.value?.form → true

4. setFieldValue 호출
   → searchFormRef.value.form.setFieldValue('prg_stat', 'S01')

5. PrimeVue Form 내부 처리
   → SelectBox 값 업데이트
   → UI 리렌더링
```

## 📝 Step 5: 조회 버튼 구현

### 5.1 handleSearch 함수

```typescript
const handleSearch = () => {
  // ⭐ searchParams는 이미 최신 상태
  // SearchForm이 자동으로 업데이트하므로 추가 로직 불필요
  emit('search');
};
```

### 5.2 Parent에서 처리

```vue
<!-- index.vue -->
<template>
  <PMDP010SearchForm @search="handleSearch" />
</template>

<script lang="ts" setup>
const handleSearch = async () => {
  // ⭐ searchParams 최신 상태 사용
  await fetchMainData(searchParams.value);
  await fetchSumData(searchParams.value);
};
</script>
```

## 📝 Step 6: CSS 스타일링

### 6.1 tomms-lite-front 패턴 참고

```scss
// pmdp010SearchForm.scss
.search-form-container {
  padding: 20px;
  background-color: var(--bg-1);
  border-radius: 8px;
  margin-bottom: 16px;
  
  :deep(.p-float-label) {
    margin-bottom: 1rem;
  }
  
  :deep(.p-button) {
    min-width: 100px;
  }
}
```

### 6.2 반응형 레이아웃

```scss
.search-form-group {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}
```

## 📝 Step 7: 완성 코드

**⚠️ CRITICAL: SearchFormRow를 사용하여 필드를 가로 배치해야 합니다!**

```vue
<template>
  <SearchForm
    ref="searchFormRef"
    :initialValues="initialValues"
    @submit="handleSubmit"
    @reset="handleReset"
  >
    <!-- ⭐ CRITICAL: SearchFormRow로 감싸서 가로 배치 -->
    <SearchFormRow>
      <SearchFormField v-slot="{ props, invalid }" name="prg_stat">
        <SearchFormLabel>진행상태</SearchFormLabel>
        <SearchFormContent>
          <Select
            v-bind="props"
            :invalid="invalid"
            :options="prgStatOptions"
            optionLabel="name"
            optionValue="value"
          />
        </SearchFormContent>
      </SearchFormField>

      <SearchFormField v-slot="{ props, invalid }" name="canc_stat">
        <SearchFormLabel>철회상태</SearchFormLabel>
        <SearchFormContent>
          <Select
            v-bind="props"
            :invalid="invalid"
            :options="cancStatOptions"
            optionLabel="name"
            optionValue="value"
          />
        </SearchFormContent>
      </SearchFormField>

      <!-- ⭐ SearchFormFieldGroup: 날짜유형 + 날짜범위 묶기 -->
      <SearchFormFieldGroup>
        <SearchFormField v-slot="{ props }" name="searchDtType">
          <SearchFormLabel>조회일자</SearchFormLabel>
          <SearchFormContent>
            <Select
              v-bind="props"
              :options="searchDtTypeOptions"
              optionLabel="name"
              optionValue="value"
            />
          </SearchFormContent>
        </SearchFormField>
        <SearchFormField v-slot="{ props }" name="searchDt">
          <SearchFormContent>
            <DatePicker
              v-bind="props"
              :numberOfMonths="2"
              selectionMode="range"
              showIcon
              iconDisplay="input"
              style="min-width: 255px"
            />
          </SearchFormContent>
        </SearchFormField>
      </SearchFormFieldGroup>
    </SearchFormRow>

    <SearchFormRow>
      <SearchFormField v-slot="{ props, invalid }" name="cont_no">
        <SearchFormLabel>계약번호</SearchFormLabel>
        <SearchFormContent>
          <InputText v-bind="props" :invalid="invalid" placeholder="계약번호 입력" />
        </SearchFormContent>
      </SearchFormField>
    </SearchFormRow>
  </SearchForm>
</template>

<script lang="ts" setup>
import { ref, computed, inject, watch, onMounted } from 'vue';
import type { Ref } from 'vue';
import {
  SearchForm,
  SearchFormContent,
  SearchFormField,
  SearchFormFieldGroup,
  SearchFormRow,
} from '@/components/common/searchForm';
import SearchFormLabel from '@/components/common/searchForm/SearchFormLabel.vue';
import { Button } from '@/components/common/button';
import { DatePicker } from '@/components/common/datePicker';
import InputText from '@/components/common/inputText/InputText.vue';
import Select from '@/components/common/select/Select.vue';
import type { PMDP010SearchParams } from '@/api/pages/sy/ds/types';
import { useCommonCodeStore } from '@/stores/commonCodeStore';

interface Emits {
  (e: 'search'): void;
}
const emit = defineEmits<Emits>();

const searchParams = inject<Ref<PMDP010SearchParams>>('searchParams')!;
const commonCodeStore = useCommonCodeStore();
const searchFormRef = ref();

const initialValues = {
  prg_stat: '',
  canc_stat: '',
  cont_no: '',
  searchDtType: 'askDt',
  searchDt: null,
};

onMounted(async () => {
  await commonCodeStore.loadMulti([
    {
      QueryId: 'MNPS010Query.StatComboIn',
      customParam: 'BUSN_SC_IN=A1 PROG_ID=PMDP010',
    },
    {
      QueryId: 'COM_PBL_0005',
      whereClause: "P_CODE_CD='C'",
    },
  ]);
});

const prgStatOptions = computed(() =>
  commonCodeStore.options('MNPS010Query.StatComboIn', true, '전체', 'ALL')
);
const cancStatOptions = computed(() =>
  commonCodeStore.options('COM_PBL_0005', true, '전체', 'ALL', "P_CODE_CD='C'")
);
const searchDtTypeOptions = [
  { name: '의뢰일자', value: 'askDt' },
  { name: '요청일자', value: 'reqDt' },
];

// ⭐⭐⭐ CRITICAL: SelectBox 동기화 watch
watch(
  () => searchParams.value?.prg_stat,
  (newVal) => {
    if (newVal !== undefined && searchFormRef.value?.form) {
      searchFormRef.value.form.setFieldValue('prg_stat', newVal ?? '');
    }
  }
);

watch(
  () => searchParams.value?.canc_stat,
  (newVal) => {
    if (newVal !== undefined && searchFormRef.value?.form) {
      searchFormRef.value.form.setFieldValue('canc_stat', newVal ?? '');
    }
  }
);

const handleSubmit = () => {
  emit('search');
};

const handleReset = () => {
  // 초기화 시 추가 로직
};

defineExpose({
  searchFormRef,
});
</script>

<style scoped lang="scss" src="./PMDP010SearchForm.scss"></style>
```

## ✅ 구현 완료 체크리스트

### 기본 구조
- [ ] SearchForm 컴포넌트 import
- [ ] searchFormRef ref 생성
- [ ] searchParams inject
- [ ] defineExpose({ searchFormRef })

### 공통코드
- [ ] onMounted에서 commonCodeStore.loadMulti 호출
- [ ] computed로 options 정의
- [ ] QueryId와 whereClause 확인

### SearchFormConfig
- [ ] groups 배열 정의
- [ ] fields 배열 정의
- [ ] 각 필드의 component, props 설정
- [ ] options에 computed 사용

### watch 패턴
- [ ] watch(() => searchParams.value?.prg_stat) 구현
- [ ] 조건: newVal !== undefined
- [ ] Ref 접근: searchFormRef.value.form.setFieldValue
- [ ] null 처리: newVal ?? ''

### 조회 버튼
- [ ] handleSearch 함수 구현
- [ ] emit('search') 호출

### CSS
- [ ] tomms-lite-front 스타일 참고
- [ ] 반응형 레이아웃 구현

## 🐛 자주 발생하는 에러

### 1. SelectBox가 업데이트되지 않음

**증상**: 진행상태 버튼 클릭 시 SelectBox 값이 변하지 않음.

**원인**:
```typescript
// ❌ WRONG
if (newVal) {
  searchFormRef.value.form.setFieldValue('prg_stat', newVal);
}
```

**해결**:
```typescript
// ✅ CORRECT
if (newVal !== undefined && searchFormRef.value?.form) {
  searchFormRef.value.form.setFieldValue('prg_stat', newVal ?? '');
}
```

### 2. searchFormRef.value.form is undefined

**증상**: `Cannot read properties of undefined (reading 'setFieldValue')`

**원인**:
```typescript
// ❌ WRONG
searchFormRef.value.value.form.setFieldValue(...)
```

**해결**:
```typescript
// ✅ CORRECT
searchFormRef.value.form.setFieldValue(...)
```

### 3. 공통코드 로딩 안됨

**증상**: Select 옵션이 비어있음.

**원인**:
```typescript
// ❌ WRONG - computed 없이 직접 사용
props: {
  options: prgStatOptions,  // computed 사용
}
```

**해결**:
```typescript
// ✅ CORRECT - computed 사용
const prgStatOptions = computed(() => 
  commonCodeStore.options('MNPS010Query.StatComboIn', true, '전체', 'ALL')
);

props: {
  options: prgStatOptions,
}
```

## 🎯 다음 단계

SearchForm 구현이 완료되었다면 **[04_DataTable_구현.md](./04_DataTable_구현.md)**로 이동하세요.
