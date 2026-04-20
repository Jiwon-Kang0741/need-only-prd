# Nexacro to Vue 완벽 변환 가이드

## 📚 문서 개요

이 폴더는 **htomss/htomss-ui (Nexacro)** 화면을 **pfy-front (Vue 3 + TypeScript)**로 변환하는 완벽한 가이드를 제공합니다.

**프로젝트 구조**:
- **소스 화면**: `htomss/htomss-ui` (Nexacro XFDL 파일)
- **타겟 프로젝트**: `pfy-front/src/pages` (Vue 3 + TypeScript)
- **백엔드**: `pfy` (Spring Boot + MyBatis)

PMDP010과 SPOV010의 패턴을 참조하여 동일한 품질로 화면을 개발합니다.

## 🚫 단일 Vue 파일 금지 (CRITICAL!)

**모든 화면은 반드시 다중 파일 구조로 생성! 하나의 vue_page에 모든 기능을 넣지 마세요!**
**⚠️ SumGrid는 스펙에 진행상태별 집계/필터링이 명시된 경우에만 생성! 단순 목록 화면에는 불필요!**

## 📛 파일 네이밍 규칙 (CRITICAL!)

**screenId는 반드시 camelCase! 모두 소문자 금지!**

```
❌ cpmsedupondgedit  → 잘못됨 (모두 소문자)
✅ cpmsEduPondgEdit  → 올바름 (camelCase)

❌ cpmsedupondglst   → 잘못됨
✅ cpmsEduPondgLst   → 올바름
```

## 🎯 필수 파일 구조

**⚠️ CRITICAL**: 새 화면을 만들 때 반드시 아래 파일을 모두 생성해야 합니다!
- screenId는 **camelCase** (모두 소문자 금지!)
- 타입은 `api/pages/[module]/[category]/types.ts`에 정의 (화면 폴더 안에 types.ts 넣지 않음!)

```
pages/[module]/[category]/[screenId]/              ← camelCase! (예: cpmsEduPondgEdit/)
  ├── index.vue                                    ← 메인 페이지 (오케스트레이터 역할만!)
  ├── [screenId].scss                              ← 화면 스타일 (예: cpmsEduPondgEdit.scss)
  └── components/                                  ← components 폴더 (필수!)
      ├── [screenId]SearchForm/                    ← 예: cpmsEduPondgEditSearchForm/
      │   ├── [ScreenId]SearchForm.vue             ← 예: CpmsEduPondgEditSearchForm.vue
      │   └── [ScreenId]SearchForm.scss            ← 컴포넌트 스타일 (필수!)
      ├── [screenId]DataTable/                     ← 예: cpmsEduPondgEditDataTable/
      │   ├── [ScreenId]DataTable.vue              ← 예: CpmsEduPondgEditDataTable.vue
      │   ├── [ScreenId]DataTable.scss             ← 컴포넌트 스타일 (필수!)
      │   └── utils/                               ← DataTable만 utils 폴더!
      │       └── index.ts                         ← getColumns/getRows 함수
      └── [screenId]SumGrid/                       ← ⚠️ 선택: 진행상태별 집계 필터가 스펙에 있을 때만!
          ├── [ScreenId]SumGrid.vue
          └── [ScreenId]SumGrid.scss

api/pages/[module]/[category]/
  ├── types.ts                                     ← 타입 정의 (공통 types.ts) ⭐
  └── [screenId].ts                                ← API 함수 (예: cpmsEduPondgEdit.ts)
```

**각 컴포넌트마다 SCSS 파일이 필요한 이유**:
- 컴포넌트별 스타일 분리 관리
- 성능 최적화 CSS 포함 (DataTable의 경우)
- pfy-front 스타일 복제
- 스타일 충돌 방지

## 📖 문서 구조

### 1. 핵심 문서 (필독!)

1. **[00_시작하기.md](./00_시작하기.md)** ⭐️ 가장 먼저 읽어야 함
   - 전체 프로세스 개요
   - 사전 준비사항
   - 개발 환경 설정
   - 프로젝트 구조 이해

2. **[12_커스텀_컴포넌트_가이드.md](./12_커스텀_컴포넌트_가이드.md)** ⭐️ 컴포넌트 사용 전 필독
   - 40+ 커스텀 컴포넌트 완벽 가이드
   - Import 패턴 결정 규칙
   - Props/Events/Slots 문서화
   - 실전 사용 시나리오
   - Quick Reference Table

2. **[01_화면_분석_단계.md](./01_화면_분석_단계.md)**
   - Nexacro XFDL 파일 분석 방법
   - 컴포넌트 매핑 전략
   - API/Mapper XML 분석 방법

3. **[02_컴포넌트_구조_설계.md](./02_컴포넌트_구조_설계.md)**
   - 폴더/파일 구조 표준
   - 컴포넌트 분리 원칙
   - Naming Convention

4. **[03_SearchForm_구현.md](./03_SearchForm_구현.md)**
   - SearchForm 완벽 구현 가이드
   - 공통코드 로딩 패턴
   - watch를 이용한 동기화

5. **[04_DataTable_구현.md](./04_DataTable_구현.md)**
   - DataTable2 래퍼 사용법
   - 컬럼 정의 표준
   - 성능 최적화 (가상 스크롤링)

6. **[05_SumGrid_ProgressBar_구현.md](./05_SumGrid_ProgressBar_구현.md)**
   - 진행상태 컴포넌트 구현
   - searchParams 연동 패턴
   - pfy-front 스타일 복제

7. **[06_API_백엔드_연동.md](./06_API_백엔드_연동.md)**
   - API 타입 정의
   - camelCase 파라미터 전달 패턴
   - MyBatis 파라미터 매핑 규칙

8. **[07_CSS_스타일링.md](./07_CSS_스타일링.md)**
   - pfy-front 스타일 복제 전략
   - SCSS 변수 활용
   - 반응형 레이아웃

9. **[08_상태관리_패턴.md](./08_상태관리_패턴.md)**
   - provide/inject 패턴
   - Pinia Store 활용
   - searchParams 동기화

10. **[09_체크리스트.md](./09_체크리스트.md)**
    - 개발 전 체크리스트
    - 개발 중 체크리스트
    - 완료 전 체크리스트

11. **[10_Router_등록.md](./10_Router_등록.md)**
    - Vue Router 등록 방법
    - path/name 규칙
    - 화면 이동 패턴

12. **[11_공통코드_로딩.md](./11_공통코드_로딩.md)**
    - useCommonCodeStore 사용법
    - onMounted 일괄 로드 패턴
    - 동적 코드 로딩 (차수 변경 시)
    - computed 옵션 정의

13. **[12_커스텀_컴포넌트_가이드.md](./12_커스텀_컴포넌트_가이드.md)** ⭐️ 가장 중요!
    - Button, InputText, Select 등 Form 컴포넌트
    - Badge, Chip, DotStatusText 등 Display 컴포넌트
    - Dialog, ConfirmDialog, Toast 등 Feedback 컴포넌트
    - DataTable, TreeTable, Chart 등 Data Display
    - 각 컴포넌트별 import 패턴, Props, Events
    - 실전 사용 시나리오 및 예제 코드

### 2. 참고 문서

- **[자주_발생하는_에러.md](./자주_발생하는_에러.md)** - 실제 발생한 에러 및 해결 방법
- **[성능_최적화_가이드.md](./성능_최적화_가이드.md)** - DataTable 성능 개선 기법 (97% 개선)
### 3. 실제 구현 예제

> ✅ **PMDP020**을 완벽한 참고 예제로 사용하세요!
> - **pfy-front 프로젝트**: `src/pages/sy/ds/pmdp020/`
>   - 폴더 구조: `components/` 서브디렉토리 사용
>   - API 연동: 실제 백엔드와 통신
>   - ContentHeader: 제대로 적용됨
> 
> - **pfy-front 프로젝트**: `src/pages/sy/ds/spov010/`
>   - 스타일링 패턴 참고용

## 🎯 핵심 원칙

### 1. **다중 파일 구조 100% 준수 + camelCase 네이밍** (최우선!)
```
❌ 잘못된 방법 1 - 단일 Vue 파일
pages/edu/pondg/cpmsEduPondgLst/
  └── index.vue  ← SearchForm, DataTable, API 모두 포함 (절대 금지!)

❌ 잘못된 방법 2 - 모두 소문자
pages/edu/pondg/cpmsedupondglst/  ← 잘못됨!

❌ 잘못된 방법 3 - 컴포넌트를 루트에 배치
pages/edu/pondg/cpmsEduPondgLst/
  ├── CpmsEduPondgLstSearchForm.vue  ← 루트에 직접 위치 (잘못됨!)

✅ 올바른 방법 - 다중 파일 + camelCase
pages/edu/pondg/cpmsEduPondgLst/
  ├── index.vue                      ← 오케스트레이터 역할만
  ├── cpmsEduPondgLst.scss
  └── components/                    ← components 폴더 필수!
      ├── cpmsEduPondgLstSearchForm/
      │   ├── CpmsEduPondgLstSearchForm.vue
      │   └── CpmsEduPondgLstSearchForm.scss
      ├── cpmsEduPondgLstDataTable/
      │   ├── CpmsEduPondgLstDataTable.vue
      │   └── CpmsEduPondgLstDataTable.scss
```

### 2. **ContentHeader 필수 포함**
```vue
<!-- ❌ 잘못된 방법 - ContentHeader 없음 -->
<template>
  <div class="pmdp020-container">
    <PMDP020SearchForm />

<!-- ✅ 올바른 방법 - PMDP020 패턴 따르기 -->
<template>
  <div class="main-content-container">
    <ContentHeader menuId="PMDP020" />
    <PMDP020SearchForm />
```

### 3. **searchParams watch 패턴 (필수!)**
```typescript
// SearchForm에서 항상 이 패턴 사용
watch(
  () => searchParams.value?.prg_stat,
  (newVal) => {
    if (newVal !== undefined && searchFormRef.value?.form) {
      searchFormRef.value.form.setFieldValue('prg_stat', newVal ?? '');
    }
  }
);
```

### 4. **API 파라미터 — camelCase 직접 전달**
```typescript
// PFY 백엔드는 camelCase 파라미터 사용 (MyBatis + DTO)
// 프론트엔드에서 변환 없이 그대로 전달
const params = { langCd: 'KO', pgmId: 'WIN', useYn: 'Y' };
const result = await selectWindowList(params);
```

### 5. **성능 최적화 (필수!)**
```vue
<!-- DataTable 성능 최적화 -->
<DataTable
  scrollHeight="540px"
  :virtualScrollerOptions="{ itemSize: 46 }"
/>
```

```scss
// CSS 성능 최적화
tr {
  will-change: background-color;
}
td {
  contain: layout style;
}
```

## 🚀 빠른 시작

### 1단계: 문서 순서대로 읽기
```bash
00_시작하기.md
01_화면_분석_단계.md
02_컴포넌트_구조_설계.md
... (순서대로)
```

### 2단계: 실제 코드 참고
```bash
# pfy-front의 PMDP020 구현 확인
code src/pages/sy/ds/pmdp020/

# pfy-front의 spov010 패턴 확인
code src/pages/sy/ds/spov010/
```

### 3단계: 새 화면 개발
```bash
09_체크리스트.md를 보며 단계별 진행
```

## ⚠️ 주의사항

### 절대 하지 말아야 할 것들

1. **❌ 단일 Vue 파일로 모든 기능 포함 (CRITICAL!)**
   - SearchForm, DataTable, API를 하나의 파일에 넣지 마세요
   - 반드시 다중 파일 구조로 분리

5. **❌ 스펙에 없는 SumGrid 자동 생성**
   - SumGrid는 진행상태별 집계 필터가 스펙에 명시된 경우에만 생성
   - 단순 목록 조회/CRUD 화면에서는 SumGrid를 생성하지 마세요

2. **❌ screenId를 모두 소문자로 작성 (CRITICAL!)**
   - `cpmsedupondgedit` → 잘못됨!
   - `cpmsEduPondgEdit` → 올바름! (camelCase 필수)

3. **❌ 다중 파일 구조 무시**
   - 컴포넌트를 루트에 직접 배치하지 말고 **components/ 폴더 사용**

4. **❌ ContentHeader 누락**
   - 모든 화면은 반드시 ContentHeader를 포함해야 함

3. **❌ ref 접근 경로 혼동**
   ```typescript
   // ❌ 잘못된 경로
   searchFormRef.value?.form?.value.setFieldValue()
   
   // ✅ 올바른 경로 (Vue ref auto-unwrap)
   searchFormRef.value?.form.setFieldValue()
   ```

4. **❌ 파라미터 대소문자 무시**
   - 백엔드는 **대문자만** 인식

5. **❌ 성능 최적화 생략**
   - 가상 스크롤링, GPU 가속 등 필수

6. **❌ watch 조건 잘못 작성**
   ```typescript
   // ❌ 빈 값 처리 안됨
   if (newVal) { ... }
   
   // ✅ undefined만 제외
   if (newVal !== undefined) { ... }
   ```

## 📞 도움말

- **에러 발생 시**: `자주_발생하는_에러.md` 참고
- **성능 문제**: `성능_최적화_가이드.md` 참고


## 📝 버전

- **작성일**: 2025-01-06
- **기준 프로젝트**: PMDP020 (완벽히 구현됨) — PFY: `src/pages/sy/ds/pmdp020/`
- **참고 프로젝트**: SPOV010 패턴 — PFY: `src/pages/sy/ds/spov010/`

---

**이 가이드를 따르면 PMDP020과 동일한 품질의 화면을 개발할 수 있습니다!**
