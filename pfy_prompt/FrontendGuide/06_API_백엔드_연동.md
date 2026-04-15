# 06. API 백엔드 연동

## 📋 이 단계의 목적

Vue 프론트엔드와 PFY Spring Boot 백엔드를 연동하여 데이터를 주고받습니다.

---

## 🔧 API 파일 생성 (CRITICAL!)

**⚠️ API 파일명은 반드시 camelCase! 모두 소문자 금지!**

```
❌ api/pages/sy/ar/syar030.ts     ← 잘못됨 (모두 소문자일 때)
✅ api/pages/sy/ar/syar030.ts     ← 올바름 (camelCase)
```

### Types 파일 위치 (CRITICAL!)

**⚠️ CRITICAL: 타입 파일은 화면별로 `{screenId}Types.ts`로 생성합니다!**

#### ✅ 올바른 패턴
```
api/pages/{module}/{category}/{screenId}Types.ts
```

**예시**:
- `api/pages/sy/ar/syar030Types.ts` - SYAR030 화면의 타입
- `api/pages/edu/pondg/cpmsEduPondgEditTypes.ts` - 교육과정 수정 화면의 타입

#### ❌ 잘못된 패턴
```
pages/{module}/{category}/{screenId}/types.ts  ← 화면 폴더 안 (잘못됨!)
api/pages/{module}/{category}/types.ts         ← 공유 types.ts (PFY 표준 아님!)
```

**이유**:
- 화면별로 타입을 분리하여 충돌 방지
- API 파일과 같은 위치에 있어 import 경로가 간단함
- PFY 프로젝트 전체에서 일관된 패턴 유지 (SYAR030, SYBJ010 등 참고)

### 기본 구조

**⚠️ API 파일명은 camelCase! (예: `syar030.ts`)**

```typescript
/**
 * syar030 - 화면관리
 * API 함수
 * 파일 위치: api/pages/sy/ar/syar030.ts (camelCase!)
 */

// ⭐ CRITICAL: 직접 axios import
import api from '@/plugins/axios';
import { ApiResponse } from '@/types/api';
import { formatErrorMessage } from '@/utils/formatErrorMessage';

// ⭐ CRITICAL: 같은 디렉토리의 타입 파일에서 import
import {
  SelectWindowListParams,
  SelectWindowListResponse,
  SaveWindowListParams,
} from '@/api/pages/sy/ar/syar030Types';

// ⭐ CRITICAL: API 엔드포인트 URL 형식
const Api = {
  selectWindowList: '/online/mvcJson/SYAR030-selectWindowList',
  saveWindowList: '/online/mvcJson/SYAR030-saveWindowList',
} as const;

/**
 * 화면 목록 조회
 * @param params 검색 파라미터
 */
export async function selectWindowList(
  params: SelectWindowListParams
): Promise<ApiResponse<SelectWindowListResponse[]>> {
  try {
    const response = await api.post<ApiResponse<SelectWindowListResponse[]>>(
      Api.selectWindowList,
      params
    );

    if (response.data.header.responseCode !== 'S0000') {
      throw new Error(
        formatErrorMessage(response, 'Failed to get Window List')
      );
    }

    return response.data;
  } catch (error: any) {
    throw new Error(formatErrorMessage(error, 'Failed to get Window List'));
  }
}

/**
 * 화면 목록 저장 (등록/수정/삭제)
 * @param params 저장 데이터 배열 (status 필드 포함)
 */
export async function saveWindowList(
  params: SaveWindowListParams[]
): Promise<ApiResponse<void>> {
  try {
    const response = await api.post<ApiResponse<void>>(
      Api.saveWindowList,
      params
    );

    if (response.data.header.responseCode !== 'S0000') {
      throw new Error(
        formatErrorMessage(response, 'Failed to save Window List')
      );
    }

    return response.data;
  } catch (error: any) {
    throw new Error(formatErrorMessage(error, 'Failed to save Window List'));
  }
}
```

**중요 규칙**:
- ✅ `import api from '@/plugins/axios'` 직접 import
- ✅ Types: `api/pages/{module}/{category}/{screenId}Types.ts`
- ✅ API import: `from '@/api/pages/{module}/{category}/{screenId}Types'`
- ✅ API URL: `/online/mvcJson/SYAR030-selectWindowList`
- ❌ API URL: `/SYAR030-selectWindowList` (prefix 누락)
- ❌ API URL: `/json/SYAR030-selectWindowList` (잘못된 prefix)
- ✅ `return response.data` (ApiResponse 전체 반환)
- ✅ **조회 포함 모든 API 호출은 `api.post()` 사용** — `api.get()` 절대 사용 금지
- ❌ `api.get(url, { params })` — CPMS `/online/mvcJson/` 디스패처는 GET을 처리하지 않음 (404/405)

---

## 📝 Step 1: 백엔드 DTO/Mapper 파라미터 분석 (CRITICAL!)

### 1.1 Mapper XML 확인

PFY 백엔드는 **MyBatis**를 사용하며, 파라미터는 **camelCase**입니다.

```xml
<!-- src/main/resources/biz/sy/mybatis/mappers/SYAR030Mapper.xml -->

<select id="selectWinList"
        parameterType="biz.sy.dto.request.WindowReqDto"
        resultType="biz.sy.dto.response.WindowResDto">
    SELECT A.lbl_cd AS "lblCd"
         , A.pgm_id AS "pgmId"
         , A.pgm_desc AS "pgmDesc"
         , A.use_yn AS "useYn"
         , A.update_uid AS "lastMdfrId"
         , A.update_dt AS "lastMdfcDtm"
      FROM cmn_pgm A
     WHERE A.lbl_cd = #{lblCd}
    <if test='pgmId != null and pgmId != ""'>
       AND UPPER(A.pgm_id) LIKE CONCAT('%', UPPER(#{pgmId}), '%')
    </if>
    <if test='useYn != null and useYn != ""'>
       AND A.use_yn = #{useYn}
    </if>
     ORDER BY A.pgm_id
</select>
```

### 1.2 핵심 발견

#### ⚠️ DO: 모든 파라미터는 camelCase (Java DTO 필드명과 동일)

```xml
<!-- ✅ CORRECT — camelCase -->
#{lblCd}
#{pgmId}
#{useYn}
```

#### ⚠️ DON'T: 대문자/snake_case 파라미터

```xml
<!-- ❌ WRONG — MyBatis에서 바인딩 실패 -->
#{LBL_CD}
#{PGM_ID}
#{USE_YN}
```

#### ⚠️ DO: MyBatis `<if test>` 조건 이해

```xml
<if test='pgmId != null and pgmId != ""'>
   AND UPPER(A.pgm_id) LIKE CONCAT('%', UPPER(#{pgmId}), '%')
</if>
```

**의미**:
- `pgmId != null`: 파라미터가 null이 아닌가?
- `pgmId != ""`: 빈 문자열이 아닌가?
- 둘 다 true → WHERE 절 추가

**결과**:
- `pgmId` 파라미터 없음/null → 조건 제외 (전체 조회)
- `pgmId = 'WIN'` → `WHERE UPPER(A.pgm_id) LIKE '%WIN%'`
- `pgmId = ''` → 조건 제외 (빈 문자열은 제외)

## 📝 Step 2: TypeScript 타입 정의

### 2.1 타입 파일 생성 위치 (CRITICAL!)

**⚠️ CRITICAL: 타입 파일은 API 폴더에 화면별로 생성합니다!**

```bash
# ✅ 올바른 위치
src/api/pages/sy/ar/syar030Types.ts

# ❌ 잘못된 위치
# src/pages/sy/ar/syar030/types.ts       ← 화면 폴더 안
# src/api/pages/sy/ar/types.ts           ← 공유 types.ts
```

### 2.2 SearchParams 인터페이스

```typescript
// syar030Types.ts

// 검색 파라미터 — camelCase (백엔드 ReqDto 필드명과 동일)
export interface SelectWindowListParams {
  langCd?: string;
  windowId?: string;
  windowNm?: string;
  useYn?: string;
}
```

**주의**:
- 프론트엔드: `langCd` (camelCase)
- 백엔드 DTO: `langCd` (camelCase — 동일!)
- **UPPERCASE 변환 불필요** — camelCase 그대로 전송

### 2.3 응답 인터페이스

```typescript
// 조회 응답 — 백엔드 ResDto 필드명과 동일 (camelCase)
export interface SelectWindowListResponse {
  lblCd: string;
  pgmId: string;
  pgmDesc?: string;
  useYn: string;
  lastMdfrId?: string;
  lastMdfcDtm?: string;
}
```

### 2.4 저장 파라미터 인터페이스

```typescript
// 저장 파라미터 — status 필드 필수 (GridStatus)
export interface SaveWindowListParams {
  status: string;       // 'I' (등록) | 'U' (수정) | 'D' (삭제)
  lblCd: string;
  pgmId: string;
  pgmDesc?: string;
  useYn: string;
}
```

**GridStatus 매핑**:

| 프론트엔드 status | 백엔드 GridStatus | 설명 |
|-------------------|-------------------|------|
| `'I'` | `GridStatus.INSERTED` | 신규 등록 |
| `'U'` | `GridStatus.UPDATED` | 수정 |
| `'D'` | `GridStatus.DELETED` | 삭제 |

## 📝 Step 3: API 함수 작성

### 3.0 백엔드 응답 구조 확인 (CRITICAL!)

PFY 백엔드의 모든 API 응답은 `ApiResponse<T>` 래퍼로 반환됩니다.

```typescript
// 공통 응답 구조
interface ApiResponse<T> {
  header: {
    responseCode: string;    // 'S0000' = 성공
    responseMessage: string;
  };
  payload: T;
}
```

#### 패턴 1: 목록 조회 (List 반환)
```java
// 백엔드 ServiceImpl
@ServiceId("SYAR030/selectWindowList")
@Transactional(readOnly = true)
public List<WindowResDto> selectWindowList(WindowReqDto request) {
    return syar030DaoImpl.selectWinList(request);
}
```

```typescript
// 프론트엔드 API
export async function selectWindowList(
  params: SelectWindowListParams
): Promise<ApiResponse<SelectWindowListResponse[]>> {
  const response = await api.post<ApiResponse<SelectWindowListResponse[]>>(
    Api.selectWindowList,
    params  // camelCase 그대로 전달
  );

  if (response.data.header.responseCode !== 'S0000') {
    throw new Error(formatErrorMessage(response, 'Failed'));
  }

  return response.data;
}

// 화면 컴포넌트에서 사용
const result = await selectWindowList(searchParams.value);
fetchedWindowList.value = result.payload;  // ← payload에서 실제 데이터 접근
```

#### 패턴 2: 저장 (void 반환)
```java
// 백엔드 ServiceImpl
@ServiceId("SYAR030/saveWindowList")
@Transactional
public void saveWindowList(List<WindowResDto> list) {
    List<WindowResDto> insertList = CommonUtils.filterByStatus(list, GridStatus.INSERTED);
    List<WindowResDto> updateList = CommonUtils.filterByStatus(list, GridStatus.UPDATED);
    List<WindowResDto> deleteList = CommonUtils.filterByStatus(list, GridStatus.DELETED);
    // ...
}
```

```typescript
// 프론트엔드 API
export async function saveWindowList(
  params: SaveWindowListParams[]
): Promise<ApiResponse<void>> {
  const response = await api.post<ApiResponse<void>>(
    Api.saveWindowList,
    params  // [{ status: 'I', lblCd: '...', ... }, { status: 'U', ... }]
  );

  if (response.data.header.responseCode !== 'S0000') {
    throw new Error(formatErrorMessage(response, 'Failed'));
  }

  return response.data;
}
```

### 3.1 API 파일 생성

```bash
# 파일 생성
touch src/api/pages/sy/ar/syar030.ts
```

### 3.2 파라미터 전달 방식 (CRITICAL!)

PFY에서는 **camelCase 파라미터를 그대로 전달**합니다. 변환이 필요하지 않습니다.

```typescript
// ✅ CORRECT — camelCase 그대로 전달
const response = await api.post(Api.selectWindowList, {
  langCd: 'KO',
  windowId: 'SYAR030',
  useYn: 'Y',
});

// ❌ WRONG — 대문자 변환 불필요
const response = await api.post(Api.selectWindowList, {
  LANG_CD: 'KO',     // ← PFY에서는 사용하지 않음
  WINDOW_ID: 'SYAR030',
});
```

### 3.3 null/빈 문자열 처리

선택적 검색 조건은 null이나 빈 문자열로 전달하면 됩니다. MyBatis `<if test>` 조건이 자동으로 처리합니다.

```typescript
// 전체 조회 (필터 없음)
const params = {
  langCd: 'KO',
  windowId: '',     // ← 빈 문자열 → MyBatis <if test> 조건 제외
  useYn: null,      // ← null → MyBatis <if test> 조건 제외
};

// 특정 조건 조회
const params = {
  langCd: 'KO',
  windowId: 'SYAR',  // ← LIKE '%SYAR%' 검색
  useYn: 'Y',        // ← 사용여부 = 'Y'
};
```

### 3.4 세션 파라미터 (서버측 자동 처리)

PFY에서 세션 관련 파라미터(`langCd`, `userId` 등)는 **서버측에서 자동으로 설정**됩니다.

```java
// 백엔드 Request DTO — sLangCd는 서버측에서 자동 설정
public class WindowReqDto extends SearchBaseDto {
    private String lblCd;
    private String pgmId;
    private String useYn;
    private String sLangCd = UserContextUtil.getLangCd();  // ← 서버측 자동
}
```

**⚠️ 프론트엔드에서 세션 파라미터를 별도로 추가할 필요가 없습니다!**

```typescript
// ✅ CORRECT — 세션 파라미터 불필요
const params = {
  lblCd: 'SYAR030',
  useYn: 'Y',
  // sLangCd 미포함 → 서버에서 자동 설정
};

// ❌ WRONG — 프론트에서 세션 파라미터 직접 추가하지 않음
const params = {
  lblCd: 'SYAR030',
  useYn: 'Y',
  sLangCd: 'KO',  // ← 불필요 (서버측 처리)
};
```

### 3.5 감사 필드 (서버측 자동 처리)

저장 시 감사 필드(`fstCretDtm`, `fstCrtrId`, `lastMdfcDtm`, `lastMdfrId`)는 **서버측 `AuditBaseDto`에서 자동 설정**됩니다.

```typescript
// ✅ CORRECT — 감사 필드 미포함
const saveData = {
  status: 'I',
  lblCd: 'SYAR030',
  pgmId: 'NEW_PGM',
  useYn: 'Y',
  // fstCretDtm, lastMdfcDtm 등은 서버에서 자동 설정
};

// ❌ WRONG — 감사 필드 직접 설정하지 않음
const saveData = {
  status: 'I',
  lblCd: 'SYAR030',
  fstCretDtm: new Date().toISOString(),  // ← 불필요
  fstCrtrId: 'admin',                     // ← 불필요
};
```

### 3.6 API 함수 정의

```typescript
import api from '@/plugins/axios';
import { ApiResponse } from '@/types/api';
import { formatErrorMessage } from '@/utils/formatErrorMessage';
import type {
  SelectWindowListParams,
  SelectWindowListResponse,
  SaveWindowListParams,
} from '@/api/pages/sy/ar/syar030Types';

const Api = {
  selectWindowList: '/online/mvcJson/SYAR030-selectWindowList',
  saveWindowList: '/online/mvcJson/SYAR030-saveWindowList',
} as const;

/**
 * 화면 목록 조회
 */
export async function selectWindowList(
  params: SelectWindowListParams
): Promise<ApiResponse<SelectWindowListResponse[]>> {
  try {
    const response = await api.post<ApiResponse<SelectWindowListResponse[]>>(
      Api.selectWindowList,
      params
    );

    if (response.data.header.responseCode !== 'S0000') {
      throw new Error(formatErrorMessage(response, 'Failed to get Window List'));
    }

    return response.data;
  } catch (error: any) {
    throw new Error(formatErrorMessage(error, 'Failed to get Window List'));
  }
}

/**
 * 화면 목록 저장
 */
export async function saveWindowList(
  params: SaveWindowListParams[]
): Promise<ApiResponse<void>> {
  try {
    const response = await api.post<ApiResponse<void>>(
      Api.saveWindowList,
      params
    );

    if (response.data.header.responseCode !== 'S0000') {
      throw new Error(formatErrorMessage(response, 'Failed to save Window List'));
    }

    return response.data;
  } catch (error: any) {
    throw new Error(formatErrorMessage(error, 'Failed to save Window List'));
  }
}
```

## 📝 Step 4: index.vue에서 API 호출

### 4.1 API 호출 함수

```typescript
import { ref, onMounted } from 'vue';
import { selectWindowList, saveWindowList } from '@/api/pages/sy/ar/syar030';
import type {
  SelectWindowListParams,
  SelectWindowListResponse,
  SaveWindowListParams,
} from '@/api/pages/sy/ar/syar030Types';

// 검색 조건
const searchParams = ref<SelectWindowListParams>({
  langCd: '',
  windowId: '',
  useYn: '',
});

// 응답 데이터
const fetchedWindowList = ref<SelectWindowListResponse[]>([]);

// 로딩 상태
const loading = ref(false);

// 목록 조회
const fetchWindowList = async () => {
  try {
    loading.value = true;
    const result = await selectWindowList(searchParams.value);
    fetchedWindowList.value = result.payload;
  } catch (error) {
    console.error('목록 데이터 조회 실패:', error);
  } finally {
    loading.value = false;
  }
};

// 조회 버튼 클릭 (SearchForm에서 emit)
const handleSearch = async () => {
  await fetchWindowList();
};

// 저장
const handleSave = async (dataList: SaveWindowListParams[]) => {
  try {
    loading.value = true;
    await saveWindowList(dataList);
    await fetchWindowList();  // 저장 후 목록 재조회
  } catch (error) {
    console.error('저장 실패:', error);
  } finally {
    loading.value = false;
  }
};
```

### 4.2 초기 조회

```typescript
import { onMounted } from 'vue';

onMounted(async () => {
  await fetchWindowList();
});
```

## 📝 Step 5: 페이징 처리

### 5.1 SearchBaseDto 상속 필드

백엔드 Request DTO는 `SearchBaseDto`를 상속하여 `page`와 `size` 필드를 자동으로 가집니다.

```java
// SearchBaseDto (pfy-fw-base)
@Data
public class SearchBaseDto {
    private Integer page = 1;     // 기본값: 1
    private Integer size = 10;    // 기본값: 10
    public int getOffset() { return (page - 1) * size; }
    public int getLimit() { return size; }
}
```

프론트엔드에서 페이징이 필요한 경우:

```typescript
// 페이징 파라미터를 함께 전송
const params = {
  langCd: 'KO',
  useYn: 'Y',
  page: 1,    // 페이지 번호
  size: 20,   // 페이지 크기
};

const result = await selectWindowList(params);
```

페이징이 불필요한 화면에서는 `page`/`size`를 생략하면 기본값(page=1, size=10)이 적용됩니다.

---

## 📝 Step 6: 에러 처리

### 6.1 try-catch 패턴

```typescript
const fetchWindowList = async () => {
  try {
    loading.value = true;
    const result = await selectWindowList(searchParams.value);
    fetchedWindowList.value = result.payload;
  } catch (error: any) {
    console.error('목록 조회 실패:', error);
    // 사용자에게 에러 메시지 표시 (Toast 사용)
  } finally {
    loading.value = false;
  }
};
```

### 6.2 백엔드 에러 코드

| 코드 | 설명 |
|------|------|
| `S0000` | 성공 |
| `E0000` | 일반 오류 |
| `CM0001` | 중복 데이터 (PK 중복 체크 시) |

```java
// 백엔드에서 HscException 발생 시
if (syar030DaoImpl.checkDuplicateWindowPk(dto)) {
    throw new HscException("CM0001");  // → responseCode: "CM0001"
}
```

### 6.3 로딩 상태 표시

```vue
<template>
  <div class="page-wrapper">
    <Syar030SearchForm @search="handleSearch" />

    <Syar030DataTable
      :fetchedMainData="fetchedWindowList"
      :loading="loading"
    />
  </div>
</template>
```

## 🔧 Backend Service Registration (CRITICAL!)

### Service 구현체 확인

**PFY 패턴**:
```java
@Slf4j
@Service
public class SYAR030ServiceImpl {

    @Autowired
    private SYAR030DaoImpl syar030DaoImpl;

    @ServiceId("SYAR030/selectWindowList")
    @ServiceName("화면 목록 조회")
    @Transactional(readOnly = true)
    public List<WindowResDto> selectWindowList(WindowReqDto request) {
        log.debug("Service Method : selectWindowList, Input Param={}", request.toString());
        try {
            return syar030DaoImpl.selectWinList(request);
        } catch (Exception e) {
            throw HscException.systemError("화면 목록 조회 중 오류가 발생했습니다", e);
        }
    }

    @ServiceId("SYAR030/saveWindowList")
    @ServiceName("화면 저장")
    @Transactional
    public void saveWindowList(List<WindowResDto> list) {
        log.debug("Service Method : saveWindowList, Input Param={}", list.toString());
        List<WindowResDto> insertList = CommonUtils.filterByStatus(list, GridStatus.INSERTED);
        List<WindowResDto> updateList = CommonUtils.filterByStatus(list, GridStatus.UPDATED);
        List<WindowResDto> deleteList = CommonUtils.filterByStatus(list, GridStatus.DELETED);

        for (WindowResDto dto : insertList) {
            if (syar030DaoImpl.checkDuplicateWindowPk(dto)) {
                throw new HscException("CM0001");
            }
            syar030DaoImpl.insertWindow(dto);
        }
        syar030DaoImpl.updateWindow(updateList);
        syar030DaoImpl.deleteWindow(deleteList);
    }
}
```

**체크리스트**:
- [ ] `@Service` 어노테이션 (파라미터 없이 사용)
- [ ] `@Slf4j` 어노테이션 (Lombok)
- [ ] `@Transactional(readOnly = true)` (조회 메서드)
- [ ] `@Transactional` (저장/수정/삭제 메서드)
- [ ] `@ServiceId("SCREEN_ID/serviceName")` 형식
- [ ] `@ServiceName("서비스명")` 추가
- [ ] DAO 인터페이스 없음 — DaoImpl만 사용

---

## ✅ 구현 완료 체크리스트

### TypeScript 타입
- [ ] `api/pages/{module}/{category}/{screenId}Types.ts` 위치 확인
- [ ] SearchParams 인터페이스 정의 (camelCase — 백엔드 ReqDto와 동일)
- [ ] 응답 인터페이스 정의 (camelCase — 백엔드 ResDto와 동일)
- [ ] 저장 인터페이스에 `status: string` 필드 포함
- [ ] API 파일에서 `from '@/api/pages/.../xxxTypes'` import 확인
- [ ] 화면 컴포넌트에서 `from '@/api/pages/.../xxxTypes'` import 확인

### API 함수
- [ ] `import api from '@/plugins/axios'` 직접 import
- [ ] **모든 API 호출 `api.post()` 사용 확인 — `api.get()` 사용 금지**
- [ ] API URL: `/online/mvcJson/{화면ID}-{메서드명}` 형식
- [ ] camelCase 파라미터 직접 전달 (변환 불필요)
- [ ] 세션 파라미터(sLangCd 등) 미포함 (서버측 처리)
- [ ] 감사 필드 미포함 (서버측 AuditBaseDto 처리)
- [ ] `response.data.header.responseCode !== 'S0000'` 체크
- [ ] `return response.data` (ApiResponse 전체 반환)

### 저장 API
- [ ] 배열로 직접 전달: `api.post(url, [{ status: 'I', ... }])`
- [ ] `status` 필드: `'I'` (등록) | `'U'` (수정) | `'D'` (삭제)
- [ ] dsSearch/dsSave 래핑 사용하지 않음

### index.vue
- [ ] fetchedData ref 생성
- [ ] loading ref 생성
- [ ] fetch 함수 작성 (try/finally + loading)
- [ ] API 결과에서 `.payload` 접근
- [ ] handleSearch 함수 작성
- [ ] onMounted 초기 조회
- [ ] 에러 처리 (try-catch)

### 백엔드 확인
- [ ] `@ServiceId` 형식 확인 (프론트 API URL과 매칭)
- [ ] `@Transactional` 어노테이션 확인
- [ ] save 메서드가 `List<ResDto>` 파라미터 수신
- [ ] `CommonUtils.filterByStatus()` + `GridStatus` 패턴 사용

---

## 🐛 자주 발생하는 에러

### 0. DispatchException: TxCode is not registered (CRITICAL!)

**증상**:
```
DispatchException: TxCode[SYAR030/selectWindowList] is not registered.
```

**원인 1: @Service 어노테이션 문제**
```java
// ❌ WRONG — 빈 이름 지정
@Service("SYAR030Service-화면관리")
public class SYAR030ServiceImpl { ... }
```

**해결**:
```java
// ✅ CORRECT — 빈 이름 지정하지 않음
@Service
public class SYAR030ServiceImpl { ... }
```

**원인 2: @Transactional 어노테이션 누락**
```java
// ❌ WRONG — @Transactional 없음
@ServiceId("SYAR030/selectWindowList")
public List<WindowResDto> selectWindowList(WindowReqDto request) { ... }
```

**해결**:
```java
// ✅ CORRECT
@Transactional(readOnly = true)
@ServiceId("SYAR030/selectWindowList")
public List<WindowResDto> selectWindowList(WindowReqDto request) { ... }
```

### 1. 파라미터가 백엔드에 전달되지 않음

**증상**: MyBatis에서 `#{pgmId}` 바인딩 값이 null.

**원인**: 프론트엔드에서 백엔드 DTO 필드명과 다른 이름 사용
```typescript
// ❌ WRONG — DTO 필드명과 불일치
const params = {
  program_id: 'WIN',    // ← 백엔드 DTO에는 'pgmId'
};
```

**해결**: 백엔드 DTO의 camelCase 필드명을 그대로 사용
```typescript
// ✅ CORRECT — 백엔드 ReqDto 필드명과 동일
const params = {
  pgmId: 'WIN',         // ← ReqDto.pgmId와 일치
};
```

### 2. 저장 시 데이터가 처리되지 않음

**증상**: 저장 API 호출은 성공하지만, DB에 데이터가 반영되지 않음.

**원인**: `status` 필드 누락 또는 잘못된 값
```typescript
// ❌ WRONG — status 필드 누락
const saveData = [{ lblCd: 'KO', pgmId: 'NEW', useYn: 'Y' }];
```

**해결**: `status` 필드에 올바른 GridStatus 코드 포함
```typescript
// ✅ CORRECT — status 필드 포함
const saveData = [
  { status: 'I', lblCd: 'KO', pgmId: 'NEW', useYn: 'Y' },  // 등록
  { status: 'U', lblCd: 'KO', pgmId: 'OLD', useYn: 'N' },  // 수정
  { status: 'D', lblCd: 'KO', pgmId: 'DEL', useYn: 'Y' },  // 삭제
];
```

### 3. API URL 불일치

**증상**: 404 Not Found 또는 `TxCode not registered`.

**원인**: API URL이 백엔드 `@ServiceId`와 매칭되지 않음
```typescript
// ❌ WRONG — prefix 누락 또는 잘못된 형식
'/SYAR030-selectWindowList'
'/json/SYAR030-selectWindowList'
'/online/mvcJson/SYAR030/selectWindowList'  // ← 하이픈 아닌 슬래시
```

**해결**: 정확한 URL 형식 사용
```typescript
// ✅ CORRECT — /online/mvcJson/{화면ID}-{메서드명}
'/online/mvcJson/SYAR030-selectWindowList'
```

### 4. PK 중복 에러 (CM0001)

**증상**: 저장 시 "중복된 자료" 에러.

**원인**: 이미 존재하는 PK로 등록(`status: 'I'`) 시도
```java
// 백엔드 ServiceImpl
if (syar030DaoImpl.checkDuplicateWindowPk(dto)) {
    throw new HscException("CM0001");
}
```

**해결**: 프론트엔드에서 중복 체크 후 알림 또는 `status: 'U'`(수정)로 전송

## 🎯 다음 단계

API 연동이 완료되었다면 **[07_CSS_스타일링.md](./07_CSS_스타일링.md)**로 이동하세요.

---

## 📚 부록: 완전한 API 파일 예제 (SYAR030)

### src/api/pages/sy/ar/syar030.ts

```typescript
/**
 * SYAR030 - 화면관리
 * API 함수
 */

import api from '@/plugins/axios';
import { ApiResponse } from '@/types/api';
import { formatErrorMessage } from '@/utils/formatErrorMessage';
import type {
  SelectWindowListParams,
  SelectWindowListResponse,
  SaveWindowListParams,
} from '@/api/pages/sy/ar/syar030Types';

const Api = {
  selectWindowList: '/online/mvcJson/SYAR030-selectWindowList',
  saveWindowList: '/online/mvcJson/SYAR030-saveWindowList',
} as const;

/**
 * 화면 목록 조회
 * @param params 검색 파라미터 (camelCase — 백엔드 ReqDto와 동일)
 */
export async function selectWindowList(
  params: SelectWindowListParams
): Promise<ApiResponse<SelectWindowListResponse[]>> {
  try {
    const response = await api.post<ApiResponse<SelectWindowListResponse[]>>(
      Api.selectWindowList,
      params
    );

    if (response.data.header.responseCode !== 'S0000') {
      throw new Error(formatErrorMessage(response, 'Failed to get Window List'));
    }

    return response.data;
  } catch (error: any) {
    throw new Error(formatErrorMessage(error, 'Failed to get Window List'));
  }
}

/**
 * 화면 목록 저장 (등록/수정/삭제)
 * @param params 저장 데이터 배열 — status: 'I' | 'U' | 'D' (GridStatus)
 */
export async function saveWindowList(
  params: SaveWindowListParams[]
): Promise<ApiResponse<void>> {
  try {
    const response = await api.post<ApiResponse<void>>(
      Api.saveWindowList,
      params
    );

    if (response.data.header.responseCode !== 'S0000') {
      throw new Error(formatErrorMessage(response, 'Failed to save Window List'));
    }

    return response.data;
  } catch (error: any) {
    throw new Error(formatErrorMessage(error, 'Failed to save Window List'));
  }
}
```

### src/api/pages/sy/ar/syar030Types.ts

```typescript
/**
 * SYAR030 - 화면관리
 * 타입 정의 — 모든 필드명은 camelCase (백엔드 DTO와 동일)
 */

// 검색 파라미터
export interface SelectWindowListParams {
  langCd?: string;
  windowId?: string;
  windowNm?: string;
  useYn?: string;
}

// 조회 응답
export interface SelectWindowListResponse {
  fstCretDtm?: string;
  lastMdfrId?: string;
  lastMdfcDtm?: string;
  lblCd: string;
  pgmId: string;
  pgmDesc?: string;
  useYn: string;
}

// 저장 파라미터
export interface SaveWindowListParams {
  status: string;       // 'I' | 'U' | 'D'
  lblCd: string;
  pgmId: string;
  pgmDesc?: string;
  useYn: string;
}
```

### ✅ 핵심 체크포인트

1. **Import 방식**
   - ✅ `import api from '@/plugins/axios'`

2. **API URL 형식**
   - ✅ `/online/mvcJson/SYAR030-selectWindowList`
   - ❌ `/SYAR030-selectWindowList`
   - ❌ `/json/SYAR030-selectWindowList`

3. **파라미터 전달**
   - ✅ camelCase 그대로 전달 (`{ langCd: 'KO', pgmId: 'WIN' }`)
   - ❌ 대문자 변환 (`{ LANG_CD: 'KO' }`)
   - ❌ dsSearch 래핑 (`{ dsSearch: [params] }`)

4. **Response 처리**
   - ✅ `return response.data` (ApiResponse 전체 반환)
   - ✅ 컴포넌트에서 `result.payload`로 접근

5. **저장 Request Body**
   - ✅ 배열 직접 전달: `[{ status: 'I', ... }]`
   - ❌ dsSave 래핑: `{ dsSave: [...] }`

---
