# 06. API 백엔드 연동

## 📋 이 단계의 목적

Vue 프론트엔드와 Spring Boot 백엔드를 연동하여 데이터를 주고받습니다.

---

## 🔧 API 파일 생성 (CRITICAL!)

**⚠️ API 파일명도 반드시 camelCase! 모두 소문자 금지!**

```
❌ api/pages/edu/pondg/cpmsedupondgedit.ts  ← 잘못됨 (모두 소문자)
✅ api/pages/edu/pondg/cpmsEduPondgEdit.ts  ← 올바름 (camelCase)
```

### Types.ts 위치 (CRITICAL!)

**⚠️ CRITICAL: types.ts는 화면 폴더가 아닌 API 폴더에 위치해야 합니다!**

#### ✅ 올바른 패턴
```
api/pages/[module]/[category]/types.ts  ← 공통 types.ts
```

**예시**:
- `api/pages/sy/ds/types.ts` - PMDP020, PMDP030 등의 타입
- `api/pages/edu/pondg/types.ts` - cpmsEduPondgEdit, cpmsEduPondgLst 등의 타입

#### ❌ 잘못된 패턴
```
pages/[module]/[category]/[screenId]/types.ts  ← 각 화면 폴더 안 (잘못됨!)
```

**잘못된 예시**:
- `pages/sy/ds/pmdp030/types.ts` ❌
- `pages/edu/pondg/cpmsEduPondgEdit/types.ts` ❌

**이유**:
- 같은 카테고리의 화면들은 타입을 공유하는 경우가 많음
- API 파일과 같은 위치에 있어 import 경로가 간단함
- 프로젝트 전체에서 일관된 패턴 유지 (SPOV010, SPOD010 등 참고)

### 기본 구조

**⚠️ API 파일명도 camelCase! (예: `cpmsEduPondgEdit.ts`, `cpmsEduPondgLst.ts`)**

```typescript
/**
 * cpmsEduPondgEdit - 교육과정 수정
 * API 함수
 * 파일 위치: api/pages/edu/pondg/cpmsEduPondgEdit.ts (camelCase!)
 */

// ⭐ CRITICAL: 직접 axios import (NOT useHtomssApi)
import api from '@/plugins/axios';
import { ApiResponse } from '@/types/api';
import { formatErrorMessage } from '@/utils/formatErrorMessage';

// ⭐ CRITICAL: Types import from same directory
import {
  CpmsEduPondgEditSearchParams,
  CpmsEduPondgEditSelectListResponse,
  CpmsEduPondgEditSelectStatSumResponse,
} from './types';  // ← 같은 디렉토리의 types.ts

// ⭐ CRITICAL: API 엔드포인트 URL 형식
const Api = {
  selectDpReqStatSum: '/online/mvcJson/PMDP020-selectDpReqStatSum',
  selectDpReqList: '/online/mvcJson/PMDP020-selectDpReqList',
  processDpReqCnfm: '/online/mvcJson/PMDP020-processDpReqCnfm',
} as const;

/**
 * 일반보급 요청 집계 조회
 * @param params 검색 파라미터
 */
export async function fetchSelectDpReqStatSum(
  params: PMDP020SearchParams
): Promise<PMDP020SelectStatSumResponse> {
  try {
    const response = await api.post<ApiResponse<PMDP020SelectStatSumResponse>>(
      Api.selectDpReqStatSum,
      params
    );

    if (response.data.header.responseCode !== 'S0000') {
      throw new Error(
        formatErrorMessage(response, 'Failed to get DpReqStatSum')
      );
    }

    return response.data.payload;
  } catch (error: any) {
    throw new Error(formatErrorMessage(error, 'Failed to get DpReqStatSum'));
  }
}

/**
 * 일반보급 요청 목록 조회
 * @param params 검색 파라미터 (대문자)
 */
export const selectDpReqList = async (params: Record<string, any>) => {
  const response = await api.post<ApiResponse<any>>(API_ENDPOINTS.selectDpReqList, params);
  
  if (response.data.header.responseCode !== 'S0000') {
    throw new Error(formatErrorMessage(response, 'Failed to get DpReqList'));
  }
  
  // ⭐ CRITICAL: response.data.payload 반환
  return response.data.payload;
};
```

**중요 규칙**:
- ❌ `const { api } = useHtomssApi()` 사용하지 말 것
- ✅ `import api from '@/plugins/axios'` 직접 import
- ❌ Types: `pages/[module]/[category]/[screenId]/types.ts` (잘못됨)
- ✅ Types: `api/pages/[module]/[category]/types.ts` (올바름)
- ❌ API import: `from '@/pages/.../types'` (잘못됨)
- ✅ API import: `from './types'` (같은 디렉토리)
- ✅ Component import: `from '@/api/pages/.../types'` (화면 컴포넌트에서)
- ❌ API URL: `/PMDP020-selectDpReqList` (잘못됨)
- ✅ API URL: `/online/mvcJson/PMDP020-selectDpReqList` (올바름)
- ✅ `return response.data.payload` (올바름 - SPOV010 패턴)

---

## 📝 Step 1: HQML 파라미터 분석 (CRITICAL!)

### 1.1 HQML 파일 확인

```xml
<!-- tomms-lite-war/htomss-biz-pbl/src/main/java/hsc/htomss/web/pm/dp/hqml/PMDP010Query.hqml -->

<statement name="selectDpAskList" type="select">
<![CDATA[
  SELECT ...
  FROM TB_MT_MREP_REQ A
  WHERE 1=1
    AND A.PBL_CD = :gPBL_CD
    AND A.BUSN_SC = :BUSN_SC
    
  <#if PRG_STAT ?? & PRG_STAT != '' >
    AND A.PRG_STAT = :PRG_STAT
  </#if>
  
  <#if CANC_STAT ?? & CANC_STAT != '' >
    AND A.CANC_STAT = :CANC_STAT
  </#if>
  
  <#if CONT_NO ?? & CONT_NO != '' >
    AND A.CONT_NO LIKE :CONT_NO || '%'
  </#if>
]]>
</statement>
```

### 1.2 핵심 발견

#### ⚠️ DO: 모든 파라미터는 대문자

```xml
<!-- ✅ CORRECT -->
:PRG_STAT
:CANC_STAT
:CONT_NO
:SEARCHDT_FROM
:SEARCHDT_TO
```

#### ⚠️ DON'T: 소문자 파라미터

```xml
<!-- ❌ WRONG - HQML에서 인식하지 못함 -->
:prg_stat
:canc_stat
:cont_no
```

#### ⚠️ DO: FreeMarker 조건 이해

```xml
<#if PRG_STAT ?? & PRG_STAT != '' >
  AND A.PRG_STAT = :PRG_STAT
</#if>
```

**의미**:
- `PRG_STAT ??`: `PRG_STAT` 파라미터가 존재하는가?
- `PRG_STAT != ''`: 빈 문자열이 아닌가?
- 둘 다 true → WHERE 절 추가

**결과**:
- `PRG_STAT` 파라미터 없음 → 조건 제외 (전체 조회)
- `PRG_STAT = 'S01'` → `WHERE A.PRG_STAT = 'S01'`
- `PRG_STAT = ''` → 조건 제외 (빈 문자열은 제외)

## 📝 Step 2: TypeScript 타입 정의

### 2.1 types.ts 생성 위치 (CRITICAL!)

**⚠️ CRITICAL: types.ts는 API 폴더에 생성해야 합니다!**

```bash
# ✅ 올바른 위치
touch src/api/pages/sy/ds/types.ts
touch src/api/pages/edu/pondg/types.ts

# ❌ 잘못된 위치 (하지 마세요!)
# touch src/pages/sy/ds/pmdp020/types.ts
# touch src/pages/edu/pondg/cpmsEduPondgEdit/types.ts
```

**이유**:
- 같은 카테고리의 화면들은 타입을 공유하는 경우가 많음
- API 파일과 같은 위치에 있어 import 경로가 간단함
- 프로젝트 전체에서 일관된 패턴 유지

### 2.2 SearchParams 인터페이스

```typescript
// types.ts
export interface PMDP010SearchParams {
  // ⚠️ DO: 프론트엔드에서는 소문자 snake_case 사용
  prg_stat?: string | null;
  canc_stat?: string | null;
  cont_no?: string;
  
  // 날짜 관련
  searchDtType?: 'askDt' | 'reqDt';
  searchDt?: Date[];  // Calendar 컴포넌트 반환값
  
  // 변환 후 사용될 필드
  SEARCHDT_FROM?: string;
  SEARCHDT_TO?: string;
  
  // ... 나머지 필드
}
```

**주의**:
- 프론트엔드: `prg_stat` (소문자)
- 백엔드: `PRG_STAT` (대문자)
- **API 레이어에서 변환 필요!**

### 2.3 응답 인터페이스

```typescript
// 집계 데이터
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

// 목록 데이터
export interface PMDP010MainData {
  CONT_NO: string;
  BUSN_SC: string;
  ASK_NO: string;
  PRG_STAT: string;
  PRG_STAT_NM: string;
  IPG?: string;
  NMGD: string;
  ASK_DT?: string;
  REQ_DT?: string;
  // ... 나머지 필드
}

export interface PMDP010SelectDpAskListResponse {
  dsOutput: PMDP010MainData[];
}
```

## 📝 Step 3: API 함수 작성

### 3.0 백엔드 응답 구조 확인 (CRITICAL!)

**⚠️ CRITICAL: 백엔드 응답 구조에 따라 처리 방식이 다릅니다!**

백엔드 서비스는 두 가지 패턴으로 응답을 반환합니다:

**패턴 1: 단일 객체 반환** (PMDP020, SPOV010)
```java
// 백엔드 서비스
@Override
public Pm020SelectStatSumResDto selectDpReqStatSum(Pm020SelectStatSumReqDto request) {
    return pmdp020Dao.selectDpReqStatSum(request);  // 단일 객체 반환
}
```

```typescript
// 프론트엔드 API
export async function fetchSelectDpReqStatSum(
  params: PMDP020SearchParams
): Promise<PMDP020SelectStatSumResponse> {
  const response = await api.post<ApiResponse<PMDP020SelectStatSumResponse>>(
    Api.selectDpReqStatSum,
    params
  );
  
  return response.data.payload;  // ← 단일 객체 직접 반환
}

// 화면 컴포넌트에서 사용
const response = await fetchSelectDpReqStatSum(requestParams);
fetchedSumData.value = response;  // ← 직접 할당
```

**패턴 2: List 반환** (PMDP100)
```java
// 백엔드 서비스
@Override
public List<Pm100SelectProgressSumResDto> selectDpProgressSum(Pm100SelectProgressSumReqDto request) {
    return pmdp100Dao.selectDpProgressSum(request);  // List 반환
}
```

```typescript
// 프론트엔드 API
export const selectDpProgressSum = async (
  params: SearchParams
): Promise<SumData[]> {  // ← List 타입으로 반환
  const response = await api.post<ApiResponse<SumData[]>>(
    API_ENDPOINTS.selectDpProgressSum,
    params
  );
  
  return response.data.payload;  // ← List 직접 반환
}

// 화면 컴포넌트에서 사용
const response = await selectDpProgressSum(requestParams);
// 집계 데이터는 첫 번째 항목 사용
fetchedSumData.value = response && response.length > 0 ? response[0] : null;
// 목록 데이터는 전체 List 사용
fetchedMainData.value = response || [];
```

**판단 기준**:
1. 백엔드 서비스 메서드 반환 타입 확인
   - `Pm020SelectStatSumResDto` → 단일 객체
   - `List<Pm100SelectProgressSumResDto>` → List
2. 프론트엔드 타입 정의
   - 단일 객체: `PMDP020SelectStatSumResponse`
   - List: `PMDP100SumData[]`
3. 화면 컴포넌트에서 데이터 접근
   - 단일 객체: `fetchedSumData.value` 직접 사용
   - List (집계): `fetchedSumData.value[0]` 또는 첫 번째 항목
   - List (목록): `fetchedMainData.value` 전체 배열

### 3.0.1 필드명 불일치 처리 (CRITICAL!)

**⚠️ CRITICAL: 백엔드 DTO 필드명과 프론트엔드 타입 정의가 다를 수 있습니다!**

**문제 상황**:
- 백엔드 DTO: camelCase (`busnSc`, `sumtot`, `suma`)
- 프론트엔드 타입: 대문자 (`BUSN_SC`, `SUMTOT`, `SUMA`)
- DataTable 컬럼: 대문자 필드명 기대

**해결 방법**:

**1단계: 프론트엔드 타입을 백엔드 DTO와 일치시키기**
```typescript
// types.ts
export interface PMDP100SumData {
  busnSc: string;    // ← 백엔드 DTO와 일치 (camelCase)
  sumtot: number;
  suma: number;
  a02: number;
  b01: number;
  // ...
}
```

**2단계: DataTable utils에서 변환**
```typescript
// utils/index.ts
/**
 * camelCase를 UPPER_SNAKE_CASE로 변환
 */
function toUpperSnakeCase(str: string): string {
  return str.replace(/([A-Z])/g, '_$1').toUpperCase();
}

/**
 * 객체의 모든 키를 camelCase에서 UPPER_SNAKE_CASE로 변환
 */
function convertKeysToUpperSnakeCase(obj: any): any {
  if (!obj || typeof obj !== 'object') {
    return obj;
  }

  const result: any = {};
  for (const [key, value] of Object.entries(obj)) {
    const upperKey = toUpperSnakeCase(key);
    result[upperKey] = value;
  }
  return result;
}

/**
 * API 응답 데이터를 DataTable 형식으로 변환
 * 백엔드 DTO는 camelCase이지만 DataTable은 UPPER_SNAKE_CASE를 기대함
 */
export function getRows(data: any[]): any[] {
  if (!data || !Array.isArray(data)) {
    return [];
  }

  return data.map((row, index) => {
    // camelCase를 UPPER_SNAKE_CASE로 변환
    const convertedRow = convertKeysToUpperSnakeCase(row);
    
    return {
      ...convertedRow,
      rowIndex: index + 1,
      // 날짜 필드 포맷팅
      GOAL_YMD_FORMATTED: formatDate(convertedRow.GOAL_YMD),
    };
  });
}
```

**3단계: SumGrid에서 필드명 변환**
```typescript
// PMDP100SumGrid.vue
const sumData = computed(() => {
  if (fetchedSumData.value) {
    return fetchedSumData.value;  // camelCase 그대로 사용
  }
  return {
    sumtot: 0,
    suma: 0,
    a02: 0,
    // ...
  };
});

// 템플릿에서 소문자로 접근
<div class="progress-btn-count">
  {{ sumData[item.field.toLowerCase()] || 0 }}
</div>
```

**판단 기준**:
1. 백엔드 DTO 필드명 확인
   - `Pm100SelectProgressSumResDto.java`에서 필드명 확인
   - camelCase면 프론트엔드도 camelCase로 정의
2. DataTable 컬럼 정의 확인
   - `getColumns()`에서 `field: 'CONT_NO'` (대문자) 사용
   - `getRows()`에서 변환 필요
3. SumGrid/ProgressList에서 필드 접근
   - camelCase로 정의했으면 소문자로 접근
   - 또는 변환 함수 사용

### 3.1 pmdp010.ts 생성

```bash
# 파일 생성
touch src/api/pages/sy/ds/pmdp010.ts
```

### 3.2 파라미터 변환 함수 (CRITICAL!)

```typescript
// pmdp010.ts
import type {
  PMDP010SearchParams,
  PMDP010SelectDpAskStatSumResponse,
  PMDP010SelectDpAskListResponse,
} from './types';

/**
 * ⭐⭐⭐ CRITICAL: 프론트엔드 파라미터를 백엔드 형식으로 변환
 * 
 * 변환 규칙:
 * 1. 소문자 → 대문자 변환
 * 2. null/undefined/빈 문자열 제외
 * 3. 날짜 범위 처리
 */
function convertSearchParamsToUpperCase(params: any): any {
  const converted: any = {};
  
  // ⭐ 필드 매핑 테이블
  const fieldMapping: Record<string, string> = {
    prg_stat: 'PRG_STAT',
    canc_stat: 'CANC_STAT',
    cont_no: 'CONT_NO',
    busn_sc: 'BUSN_SC',
    ipg: 'IPG',
    ask_no: 'ASK_NO',
    sys_cd: 'SYS_CD',
    // ... 모든 필드 매핑
  };
  
  // ⭐ 일반 필드 변환
  Object.keys(params).forEach((key) => {
    const value = params[key];
    const upperKey = fieldMapping[key] || key.toUpperCase();
    
    // ⚠️ DO: null/undefined/빈 문자열 제외
    if (value !== null && value !== undefined && value !== '') {
      converted[upperKey] = value;
    }
  });
  
  // ⭐ 날짜 범위 처리
  if (params.searchDt && Array.isArray(params.searchDt)) {
    const [startDate, endDate] = params.searchDt;
    
    if (startDate) {
      converted.SEARCHDT_FROM = formatDateToYYYYMMDD(startDate);
    }
    
    if (endDate) {
      converted.SEARCHDT_TO = formatDateToYYYYMMDD(endDate);
    }
  }
  
  // ⭐ 조회일자 타입 처리
  if (params.searchDtType) {
    converted.SEARCHDTTYPE = params.searchDtType === 'askDt' ? 'ASK' : 'REQ';
  }
  
  return converted;
}

/**
 * Date 객체를 YYYYMMDD 문자열로 변환
 */
function formatDateToYYYYMMDD(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}
```

### 3.3 왜 변환이 필요한가?

#### A. null/undefined/빈 문자열 제외

```typescript
// 전체 건수 버튼 클릭
searchParams.value.prg_stat = null;

// 변환 전
{
  prg_stat: null,
  canc_stat: '',
  cont_no: undefined,
}

// 변환 후 (API 요청)
{
  // PRG_STAT, CANC_STAT, CONT_NO 모두 제외됨
}

// HQML 결과
<#if PRG_STAT ?? & PRG_STAT != '' >
  // PRG_STAT이 존재하지 않으므로 false
  // 조건이 추가되지 않음 → 전체 조회
</#if>
```

#### B. 대문자 변환

```typescript
// 변환 전
{
  prg_stat: 'S01',
  cont_no: '1234',
}

// 변환 후
{
  PRG_STAT: 'S01',
  CONT_NO: '1234',
}

// HQML에서 사용
:PRG_STAT  // ← 대문자로 인식
:CONT_NO
```

### 3.4 API 함수 정의

```typescript
import api from '@/plugins/axios';

/**
 * 의뢰 진행상태별 집계 조회
 */
export async function selectDpAskStatSum(
  params: PMDP010SearchParams
): Promise<PMDP010SelectDpAskStatSumResponse> {
  const convertedParams = convertSearchParamsToUpperCase(params);
  
  const response = await api.post<ApiResponse<PMDP010SelectDpAskStatSumResponse>>(
    '/online/mvcJson/PMDP010-selectDpAskStatSum',
    convertedParams
  );
  
  if (response.data.header.responseCode !== 'S0000') {
    throw new Error(formatErrorMessage(response, 'Failed to get DpAskStatSum'));
  }
  
  return response.data.payload;
}

/**
 * 의뢰 목록 조회
 */
export async function selectDpAskList(
  params: PMDP010SearchParams
): Promise<PMDP010SelectDpAskListResponse> {
  const convertedParams = convertSearchParamsToUpperCase(params);
  
  const response = await api.post<ApiResponse<PMDP010SelectDpAskListResponse>>(
    '/online/mvcJson/PMDP010-selectDpAskList',
    convertedParams
  );
  
  if (response.data.header.responseCode !== 'S0000') {
    throw new Error(formatErrorMessage(response, 'Failed to get DpAskList'));
  }
  
  return response.data.payload;
}
```

## 📝 Step 4: index.vue에서 API 호출

### 4.1 API 호출 함수

```typescript
import { ref } from 'vue';
import { selectDpAskStatSum, selectDpAskList } from '@/api/pages/sy/ds/pmdp010';
import type {
  PMDP010SelectDpAskStatSumResponse,
  PMDP010SelectDpAskListResponse,
} from '@/api/pages/sy/ds/types';

// 응답 데이터
const fetchedSumData = ref<PMDP010SelectDpAskStatSumResponse | null>(null);
const fetchedMainData = ref<PMDP010SelectDpAskListResponse | null>(null);

// 로딩 상태
const loading = ref(false);

// 집계 데이터 조회
const fetchSumData = async () => {
  try {
    loading.value = true;
    fetchedSumData.value = await selectDpAskStatSum(searchParams.value);
  } catch (error) {
    console.error('집계 데이터 조회 실패:', error);
  } finally {
    loading.value = false;
  }
};

// 목록 데이터 조회
const fetchMainData = async () => {
  try {
    loading.value = true;
    fetchedMainData.value = await selectDpAskList(searchParams.value);
  } catch (error) {
    console.error('목록 데이터 조회 실패:', error);
  } finally {
    loading.value = false;
  }
};

// 조회 버튼 클릭 (SearchForm에서 emit)
const handleSearch = async () => {
  await Promise.all([
    fetchSumData(),
    fetchMainData(),
  ]);
};
```

### 4.2 초기 조회

```typescript
import { onMounted } from 'vue';

onMounted(async () => {
  // 초기 조회
  await handleSearch();
});
```

## 📝 Step 5: 전역 변수 처리

### 5.1 authenticationStore 사용

```typescript
import { useAuthenticationStore } from '@/stores/authentication';

const authStore = useAuthenticationStore();

// ⭐ 모든 API 호출 시 전역 변수 자동 추가
function convertSearchParamsToUpperCase(params: any): any {
  const converted: any = {
    // ⭐ 전역 변수
    gPBL_CD: authStore.pblCd,
    gLANG: authStore.lang,
    gTYPE_CD: authStore.typeCd,
    gCOMP_CD: authStore.compCd,
  };
  
  // ... 나머지 변환 로직
  
  return converted;
}
```

### 5.2 HQML에서 사용

```xml
SELECT ...
WHERE 1=1
  AND A.PBL_CD = :gPBL_CD        -- ← 자동으로 추가됨
  AND A.LANG = :gLANG
  AND DECODE(:gLANG, 'ko_Kr', C.NMGD, C.ENG_NMGD) AS NMGD
```

## 📝 Step 6: 에러 처리

### 6.1 try-catch 패턴

```typescript
const fetchMainData = async () => {
  try {
    loading.value = true;
    fetchedMainData.value = await selectDpAskList(searchParams.value);
  } catch (error: any) {
    console.error('목록 데이터 조회 실패:', error);
    
    // ⭐ 사용자에게 에러 메시지 표시
    if (error.response?.data?.message) {
      alert(error.response.data.message);
    } else {
      alert('데이터 조회 중 오류가 발생했습니다.');
    }
  } finally {
    loading.value = false;
  }
};
```

### 6.2 로딩 상태 표시

```vue
<template>
  <div class="page-wrapper">
    <PMDP010SearchForm @search="handleSearch" />
    
    <PMDP010SumGrid
      :fetchedSumData="fetchedSumData"
    />
    
    <PMDP010DataTable
      :fetchedMainData="fetchedMainData?.dsOutput || []"
      :loading="loading"
    />
  </div>
</template>
```

## 🔧 Backend Service Registration (CRITICAL!)

### Maven Dependency 확인

새로운 모듈의 서비스가 등록되지 않는 경우:

1. **tomms-boot/pom.xml 확인**
```xml
<dependencies>
  <!-- ✅ 모든 업무 모듈이 dependency로 포함되어야 함 -->
  <dependency>
    <groupId>tomms</groupId>
    <artifactId>tomms-biz-spareparts</artifactId>
    <version>5.3.3-SNAPSHOT</version>
  </dependency>
  
  <dependency>
    <groupId>tomms</groupId>
    <artifactId>tomms-biz-purchasemgmt</artifactId>  <!-- ← 누락 시 서비스 등록 안 됨! -->
    <version>5.3.3-SNAPSHOT</version>
  </dependency>
</dependencies>
```

2. **Maven 프로젝트 재빌드**
```bash
mvn clean install
```

3. **백엔드 서버 재시작**

### Service 구현체 확인

**SPOV010 참고 패턴**:
```java
@Service  // ← 빈 이름 지정하지 않음
public class PMDP020ServiceImpl implements PMDP020Service {
    
    @Override
    @Transactional(readOnly = true)  // ← 조회 메서드는 readOnly = true
    @ServiceId("PMDP020/selectDpReqStatSum")
    @ServiceName("요청 합계 조회")
    public PmSelectStatSumResDto selectDpReqStatSum(PmSelectStatSumReqDto request) {
        // ...
    }
    
    @Override
    @Transactional  // ← 저장/수정 메서드는 readOnly 없음
    @ServiceId("PMDP020/processDpReqCnfm")
    @ServiceName("일반보급 요청 확정")
    public PmProcessResDto processDpReqCnfm(List<PmProcessReqCnfmReqDto> requestList) {
        // ...
    }
}
```

**체크리스트**:
- [ ] `@Service` 어노테이션 (빈 이름 지정하지 않음)
- [ ] `@Transactional(readOnly = true)` (조회 메서드)
- [ ] `@Transactional` (저장/수정 메서드)
- [ ] `@ServiceId("SCREEN_ID/serviceName")` 형식
- [ ] `@ServiceName("서비스명")` 추가

### Vite 프록시 설정 확인

```typescript
// vite.config.ts
const baseURL = env.VITE_API_BASE_URL || 'http://localhost:8888';  // ← 기본값 필수!

return {
  server: {
    proxy: {
      '/online/api': {
        target: baseURL,
        changeOrigin: true,
      },
      '/online/mvcJson': {
        target: baseURL,
        changeOrigin: true,
      },
    },
  },
};
```

## ✅ 구현 완료 체크리스트

### Backend Service
- [ ] `tomms-boot/pom.xml`에 모듈 dependency 추가
- [ ] `@Service` 어노테이션 (빈 이름 지정하지 않음)
- [ ] `@Transactional(readOnly = true)` 추가 (조회 메서드)
- [ ] `@ServiceId`, `@ServiceName` 어노테이션 확인
- [ ] Maven 프로젝트 재빌드
- [ ] 백엔드 서버 재시작
- [ ] 서비스 등록 확인 (로그 확인)

### Frontend Proxy
- [ ] `vite.config.ts`에 baseURL 기본값 설정
- [ ] `/online/api`, `/online/mvcJson` 프록시 설정 확인

### TypeScript 타입
- [ ] `api/pages/[module]/[category]/types.ts` 위치 확인 (공통 types.ts)
- [ ] PMDP010SearchParams 인터페이스 정의
- [ ] 응답 인터페이스 정의 (SumData, MainData)
- [ ] 프론트엔드: 소문자 snake_case
- [ ] 백엔드: 대문자 UPPER_CASE
- [ ] API 파일에서 `from './types'` import 확인
- [ ] 화면 컴포넌트에서 `from '@/api/pages/.../types'` import 확인

### 파라미터 변환
- [ ] convertSearchParamsToUpperCase 함수 작성
- [ ] fieldMapping 테이블 작성
- [ ] null/undefined/빈 문자열 필터링
- [ ] 날짜 범위 처리
- [ ] 전역 변수 추가 (gPBL_CD, gLANG 등)

### API 함수
- [ ] selectDpAskStatSum 함수 작성
- [ ] selectDpAskList 함수 작성
- [ ] convertSearchParamsToUpperCase 호출
- [ ] dsSearch 배열로 감싸기

### index.vue
- [ ] fetchedSumData, fetchedMainData ref 생성
- [ ] loading ref 생성
- [ ] fetchSumData 함수 작성
- [ ] fetchMainData 함수 작성
- [ ] handleSearch 함수 작성
- [ ] onMounted 초기 조회
- [ ] 에러 처리 (try-catch)

### HQML 확인
- [ ] 모든 파라미터 대문자 확인
- [ ] FreeMarker 조건 확인 (<#if>)
- [ ] 전역 변수 확인 (:gPBL_CD 등)

## 🐛 자주 발생하는 에러

### 0. DispatchException: TxCode[SCREEN_ID/serviceName] is not registered (CRITICAL!)

**증상**:
```
DispatchException: TxCode[PMDP020/selectDpReqStatSum] is not registered.
```

**원인 1: Maven Dependency 누락**
```xml
<!-- ❌ WRONG - tomms-boot/pom.xml에 모듈이 없음 -->
<dependencies>
  <dependency>
    <groupId>tomms</groupId>
    <artifactId>tomms-biz-spareparts</artifactId>
    <version>5.3.3-SNAPSHOT</version>
  </dependency>
  <!-- tomms-biz-purchasemgmt 누락! -->
</dependencies>
```

**해결**:
```xml
<!-- ✅ CORRECT - 모든 업무 모듈 추가 -->
<dependencies>
  <dependency>
    <groupId>tomms</groupId>
    <artifactId>tomms-biz-spareparts</artifactId>
    <version>5.3.3-SNAPSHOT</version>
  </dependency>
  
  <dependency>
    <groupId>tomms</groupId>
    <artifactId>tomms-biz-purchasemgmt</artifactId>  <!-- ← 추가! -->
    <version>5.3.3-SNAPSHOT</version>
  </dependency>
</dependencies>
```

**다음 단계**:
1. `mvn clean install` 실행
2. 백엔드 서버 재시작
3. 서비스 등록 확인 (로그에서 `PMDP020/selectDpReqStatSum` 확인)

**원인 2: @Service 어노테이션 문제**
```java
// ❌ WRONG - 빈 이름 지정
@Service("PMDP020Service-일반보급요청")
public class PMDP020ServiceImpl implements PMDP020Service {
    // ...
}
```

**해결**:
```java
// ✅ CORRECT - 빈 이름 지정하지 않음 (SPOV010과 동일)
@Service
public class PMDP020ServiceImpl implements PMDP020Service {
    // ...
}
```

**원인 3: @Transactional 어노테이션 누락**
```java
// ❌ WRONG - @Transactional 없음
@Override
@ServiceId("PMDP020/selectDpReqStatSum")
@ServiceName("요청 합계 조회")
public PmSelectStatSumResDto selectDpReqStatSum(PmSelectStatSumReqDto request) {
    // ...
}
```

**해결**:
```java
// ✅ CORRECT - @Transactional(readOnly = true) 추가 (SPOV010과 동일)
@Override
@Transactional(readOnly = true)  // ← 추가!
@ServiceId("PMDP020/selectDpReqStatSum")
@ServiceName("요청 합계 조회")
public PmSelectStatSumResDto selectDpReqStatSum(PmSelectStatSumReqDto request) {
    // ...
}
```

**SPOV010 참고 패턴**:
- 조회 메서드: `@Transactional(readOnly = true)`
- 저장/수정 메서드: `@Transactional`
- 모든 메서드에 `@ServiceId`, `@ServiceName` 필수

### 1. 파라미터가 백엔드에 전달되지 않음

**증상**: HQML에서 `PRG_STAT`이 null.

**원인**:
```typescript
// ❌ WRONG - 소문자로 전송
const response = await api.post('/online/mvcJson/PMDP010-selectDpAskList', {
  prg_stat: 'S01',  // ← 소문자
});
```

**해결**:
```typescript
// ✅ CORRECT - convertSearchParamsToUpperCase 사용
const convertedParams = convertSearchParamsToUpperCase(params);
const response = await api.post<ApiResponse<any>>('/online/mvcJson/PMDP010-selectDpAskList', convertedParams);
// ← { PRG_STAT: 'S01' } 대문자로 변환됨
```

### 2. 전체 건수 버튼 클릭 시 조회 안 됨

**증상**: 전체 버튼 클릭 시 데이터가 조회되지 않음.

**원인**:
```typescript
// ❌ WRONG - 빈 문자열이 전달됨
if (value !== null && value !== undefined) {
  converted[upperKey] = value;  // ← value = ''도 포함됨
}
```

**해결**:
```typescript
// ✅ CORRECT - 빈 문자열도 제외
if (value !== null && value !== undefined && value !== '') {
  converted[upperKey] = value;
}
```

### 3. 날짜 포맷 오류

**증상**: 날짜 조회 시 SQL 오류.

**원인**:
```typescript
// ❌ WRONG - Date 객체를 그대로 전송
converted.SEARCHDT_FROM = params.searchDt[0];  // ← Date 객체
```

**해결**:
```typescript
// ✅ CORRECT - YYYYMMDD 문자열로 변환
converted.SEARCHDT_FROM = formatDateToYYYYMMDD(params.searchDt[0]);
```

### 4. 전역 변수 누락

**증상**: SQL에서 `:gPBL_CD` 바인딩 오류.

**원인**:
```typescript
// ❌ WRONG - 전역 변수 없음
const converted: any = {};
```

**해결**:
```typescript
// ✅ CORRECT - 전역 변수 추가
const converted: any = {
  gPBL_CD: authStore.pblCd,
  gLANG: authStore.lang,
  gTYPE_CD: authStore.typeCd,
  gCOMP_CD: authStore.compCd,
};
```

## 🎯 다음 단계

API 연동이 완료되었다면 **[07_CSS_스타일링.md](./07_CSS_스타일링.md)**로 이동하세요.

---

## 📚 부록: 완전한 API 파일 예제 (PMDP010)

### src/api/pages/sy/ds/pmdp010.ts

```typescript
/**
 * PMDP010 - 물자보급의뢰
 * API 함수
 */

// ⭐ CRITICAL: 직접 axios import (useHtomssApi 사용 X)
import api from '@/plugins/axios';

// ⭐ CRITICAL: API 엔드포인트 URL 형식
const API_ENDPOINTS = {
  selectDpAskList: '/online/mvcJson/PMDP010-selectDpAskList',
  selectCanStat: '/online/mvcJson/PMDP010-selectCanStat',
  selectPblBsns: '/online/mvcJson/PMDP010-selectPblBsns',
  processDpAskInsert: '/online/mvcJson/PMDP010-processDpAskInsert',
} as const;

/**
 * 검색 파라미터를 대문자로 변환
 * @param params 원본 파라미터 (소문자)
 * @returns 변환된 파라미터 (대문자)
 */
export const convertSearchParamsToUpperCase = (params: Record<string, any>): Record<string, any> => {
  const converted: Record<string, any> = {};
  
  for (const [key, value] of Object.entries(params)) {
    // ⚠️ null, undefined, 빈 문자열 제외
    if (value !== null && value !== undefined && value !== '') {
      const upperKey = key.toUpperCase();
      converted[upperKey] = value;
    }
  }
  
  return converted;
};

/**
 * 물자보급의뢰 목록 조회
 * @param params 검색 파라미터
 */
export const selectDpAskList = async (params: Record<string, any>) => {
  const response = await api.post(API_ENDPOINTS.selectDpAskList, {
    dsSearch: [convertSearchParamsToUpperCase(params)],
  });
  
  // ⭐ CRITICAL: response.data 직접 반환 (payload 아님!)
  return response.data;
};

/**
 * 취소상태 조회
 * @param params 취소상태 파라미터
 */
export const selectCanStat = async (params: Record<string, any>) => {
  const response = await api.post(API_ENDPOINTS.selectCanStat, {
    dsSearch: [convertSearchParamsToUpperCase(params)],
  });
  
  return response.data;
};

/**
 * 사업부서 조회
 * @param params 사업부서 파라미터
 */
export const selectPblBsns = async (params: Record<string, any>) => {
  const response = await api.post(API_ENDPOINTS.selectPblBsns, {
    dsSearch: [convertSearchParamsToUpperCase(params)],
  });
  
  return response.data;
};

/**
 * 물자보급의뢰 등록
 * @param data 등록 데이터
 */
export const processDpAskInsert = async (data: Record<string, any>) => {
  const response = await api.post(API_ENDPOINTS.processDpAskInsert, {
    dsSave: [convertSearchParamsToUpperCase(data)],
  });
  
  return response.data;
};
```

### ✅ 핵심 체크포인트

1. **Import 방식**
   - ✅ `import api from '@/plugins/axios'`
   - ❌ `const { api } = useHtomssApi()`

2. **API URL 형식**
   - ✅ `/online/mvcJson/PMDP010-selectDpAskList`
   - ❌ `/PMDP010-selectDpAskList`
   - ❌ `/json/PMDP010-selectDpAskList` (잘못된 형식)

3. **Response 처리**
   - ✅ `return response.data.payload` (실제 API 응답 구조)
   - ❌ `return response.data` (잘못됨)

4. **파라미터 변환**
   - ✅ `convertSearchParamsToUpperCase()` 사용
   - ✅ null, undefined, 빈 문자열 제외
   - ✅ 대문자로 변환

5. **Request Body 구조**
   - ✅ `{ dsSearch: [params] }` 형식
   - ✅ `{ dsSave: [data] }` 형식 (저장 시)

---

