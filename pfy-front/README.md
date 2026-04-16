# TOMMS Lite Portal System (SPS) - Frontend

## 프로젝트 개요

- Vue 3 + TypeScript + Vite 기반 프론트엔드 프로젝트
- PrimeVue UI 컴포넌트 사용
- pnpm 패키지 매니저 사용

---

## 기술 스택

- 프레임워크/라이브러리: Vue 3, Pinia, PrimeVue, Axios 등
- 빌드 도구: Vite, pnpm
- 언어: TypeScript, JavaScript
- 스타일링: SCSS, PrimeVue CSS
- 린팅/포맷팅: ESLint (Airbnb), Prettier
- 기타: ECharts, DOMPurify, xlsx, jspdf 등

---

## 개발 환경 및 필수 도구

- Node.js 22 이상
- pnpm (패키지 매니저)
- VSCode 또는 IntelliJ IDEA
- Git

---

## 초기 설치 및 실행 방법

```bash
# 의존성 설치
pnpm install

# 개발 서버 실행
pnpm dev

# 빌드
pnpm build

# 빌드 결과 미리보기
pnpm preview

```

## 폴더 기본 구조

src/
├── api/ # 서버 API 호출 함수 모음
├── assets/ # 이미지, 폰트, 아이콘 등 정적 자원
├── components/ # 재사용 가능한 공통 UI 컴포넌트
├── composables/ # Vue Composition API 커스텀 훅 (useApi, useLocale 등)
├── directives/ # Vue 사용자 정의 디렉티브 모음 (domPurify 등)
├── locales/ # 다국어(국제화) 리소스 및 설정
├── pages/ # 화면 ID 기준별 Vue 컴포넌트 (각 페이지별), 라우터 연결용
│ ├── features/ # 재사용 혹은 조합하는 단위 컴포넌트 모음
├── plugins/ # 플러그인 등록 및 설정 (axios, i18n 등)
├── router/ # Vue Router 설정 파일
├── stores/ # Pinia 상태 관리 모듈
├── styles/ # 전역 SCSS, 변수, 믹스인 등 스타일 관련
├── types/ # 타입스크립트 타입 정의
├── utils/ # 공통 함수 및 유틸리티 모음
├── App.vue # 최상위 Vue 컴포넌트
└── main.ts # 앱 진입점 및 초기화


---

## 코드 스타일 가이드 및 린팅

본 프로젝트는 ESLint, Prettier, Airbnb 스타일 가이드를 기반으로 일관된 코드 스타일을 유지합니다.

- ESLint + Prettier + Airbnb 스타일 가이드 사용
- .eslintrc.cjs 및 .prettierrc.cjs 파일 참고
- VSCode 설정(.vscode/settings.json) 포함 — 저장 시 자동 포맷팅 및 린팅 적용

  - 세미콜론(`;`) 사용을 권장합니다.
  - 변수 선언 시 `const`와 `let` 사용을 권장하며, `var` 사용은 지양합니다.
  - 화살표 함수, 템플릿 문자열 등 최신 문법 사용을 권장합니다.
  - 들여쓰기는 스페이스 2칸을 사용합니다.
  - 문자열은 싱글 쿼트(`'`)를 기본으로 하며, 필요 시 더블 쿼트를 사용합니다.
  - 함수명과 변수명은 카멜 케이스(camelCase)를 사용합니다.
  - `import` 구문 시 파일 확장자는 명시하지 않습니다.
  - 불필요한 `console.log` 사용을 금지하며, 경고 또는 에러 처리합니다.

---

## 환경 설정 가이드

### 1. IntelliJ IDEA 설정

#### 1) 플러그인 설치

- `File > Settings > Plugins`의 `Martketplace`에서 `ESLint`와 `Prettier` 검색 후 설치
  (IntelliJ 최신 버전에서는 `ESLint` 기본 내장)
- IDE 재시작

#### 2) ESLint 설정

- `File > Settings > Languages & Frameworks > JavaScript > Code Quality Tools > ESLint` 이동
- `Manual ESLint configuration` 선택
- ESLint 패키지 경로가 `node_modules/eslint`로 정확히 지정되어 있는지 확인 (`~\tomms-lite-front\node_modules\eslint`)
- 프로젝트 루트(Working directories)가 작업 디렉터리로 설정되어 있는지 확인
- Configuration File에서 Configuration file 부분 `.eslintrc.cjs` 설정 파일이 인식되는지 확인
  (`프로젝트 폴더\tomms-lite-front\.eslintrc.cjs`)
- `Run for files: **/*.{js,ts,jsx,tsx,cjs,cts,mjs,mts,html,vue}`
- `Run eslint --fix on save` 옵션 체크 (저장 시 자동 수정)

#### 3) Prettier 설정

- `File > Settings > Languages & Frameworks > JavaScript > Prettier` 이동
- `Manual Prettier configuration 선택 > Prettier package 경로`
  Prettier 경로 자동 감지 (`node_modules/prettier` 또는 `~\tomms-lite-front\node_modules\prettier`)
- `Run on 'Refomat Code' action, Apply Prettier to files outside the prettier dependency scope 옵션 체크`
- `Run for files: **/*.{js,ts,jsx,tsx,cjs,cts,mjs,mts,vue,astro}`
- `Run on Save, Prefer Prettier configuration to IDE code Style 옵션 체크`

---

### 2. VSCode 설정

#### 1) 확장 프로그램 설치

- ESLint
- Prettier - Code formatter

#### 2) 워크스페이스 설정 (`.vscode/settings.json`)

- `.vscode/settings.json` 파일이 프로젝트에 포함되어 있어 별도 설정 없이도 자동 포맷팅과 린팅이 적용됩니다.
- VSCode에서 ESLint, Prettier 확장 프로그램만 설치해 주세요.

```

**- IntelliJ or VSCode 설정 후 린트 에러 및 경고가 터미널에 표시되는지 확인
- IntelliJ 혹은 VSCode에서 저장 시 자동 포맷팅 및 린팅이 적용되는지 확인**

```



