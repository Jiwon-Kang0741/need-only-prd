# pfy-front · MockUp 스캐폴딩 시스템

> 고객 공유용 MockUp 페이지를 **템플릿 기반으로 자동 생성**하는 Scaffolding 시스템.  
> LLM 코드 창작 없이, 정의한 필드 메타데이터만으로 완성된 Vue SFC + 라우터 등록까지 자동 처리.

---

## 시스템 구조

```
pfy-front/
├── scaffolding/                 ← 스캐폴딩 서버 (Node.js/Express)
│   ├── src/
│   │   ├── server.ts            ← Express 진입점 (포트 4000)
│   │   ├── types.ts             ← 공유 타입 정의
│   │   ├── generators/
│   │   │   ├── VuePageGenerator.ts   ← Vue SFC 문자열 생성 (템플릿 기반)
│   │   │   ├── MockDataGenerator.ts  ← 필드 타입별 mock 데이터 생성
│   │   │   └── RouterUpdater.ts      ← ts-morph AST 기반 라우터 등록/삭제
│   │   ├── routes/
│   │   │   └── scaffold.ts      ← REST API 라우트
│   │   └── utils/
│   │       └── paths.ts         ← 절대 경로 상수
│   ├── public/
│   │   └── index.html           ← 스캐폴딩 Web UI (Vanilla JS)
│   ├── package.json
│   └── tsconfig.json
└── src/
    ├── pages/generated/         ← ✨ 생성된 페이지가 여기에 저장됨
    │   └── {screenId}/
    │       ├── index.vue
    │       └── scaffold-meta.json
    ├── components/templates/    ← 4개의 Standard 템플릿 컴포넌트
    └── router/
        └── staticRoutes.ts      ← AST 자동 수정됨
```

---

## 실행 방법

### 1. 스캐폴딩 서버 의존성 설치

```bash
cd scaffolding
npm install
# 또는
pnpm install
```

### 2. 스캐폴딩 서버 시작

```bash
# scaffolding/ 디렉터리에서
npm start
# 또는 ts-node 직접 실행
npx ts-node src/server.ts
```

서버가 `http://localhost:4000` 에서 실행됩니다.

### 3. Vite 개발 서버 시작 (별도 터미널)

```bash
# pfy-front/ 루트에서
pnpm dev
```

Vite 서버가 `http://localhost:5173` (또는 설정된 포트)에서 실행됩니다.

### 4. 스캐폴딩 UI 접속

브라우저에서 `http://localhost:4000` 접속

---

## 사용 방법

### Web UI 사용

1. **① 기본 정보** 섹션에서 화면 ID, 이름, 타입을 입력
2. **② 필드 정의** 섹션에서 필드를 추가하고 각 속성 설정:
   - `키` — Vue 컴포넌트에서 사용할 camelCase 프로퍼티명
   - `레이블` — 화면에 표시할 한글 이름
   - `타입` — 입력 컴포넌트 타입
   - `검색/목록/상세/편집` — 해당 영역에 포함 여부
3. (tab-detail 타입) **③ 탭 정의** 섹션에서 탭 키/레이블 추가
4. **MockUp 페이지 생성** 버튼 클릭
5. 우측 **코드 미리보기**에서 생성된 코드 확인
6. Vite 서버 링크를 클릭하여 브라우저에서 바로 확인

### REST API 직접 사용

#### 페이지 생성

```bash
curl -X POST http://localhost:4000/api/scaffold \
  -H "Content-Type: application/json" \
  -d '{
    "screenId": "MNET010",
    "screenName": "신고 관리",
    "pageType": "list-detail",
    "menuPath": ["윤리경영", "부정제보", "신고 관리"],
    "fields": [
      {
        "key": "title",
        "label": "제목",
        "type": "text",
        "searchable": true,
        "listable": true,
        "detailable": true,
        "editable": true,
        "required": true
      },
      {
        "key": "status",
        "label": "처리상태",
        "type": "badge",
        "searchable": true,
        "listable": true,
        "detailable": true,
        "options": [
          { "label": "접수",   "value": "RECV", "color": "blue"   },
          { "label": "처리중", "value": "WIP",  "color": "orange" },
          { "label": "완료",   "value": "DONE", "color": "green"  }
        ]
      },
      {
        "key": "regDt",
        "label": "등록일",
        "type": "daterange",
        "searchable": true,
        "listable": true,
        "detailable": true
      }
    ]
  }'
```

응답 예시:
```json
{
  "success": true,
  "message": "✅ 신고 관리 (MNET010) 생성 완료",
  "filePath": "/absolute/path/src/pages/generated/mnet010/index.vue",
  "routePath": "/MNET010",
  "preview": "<!-- Generated ... --><template>..."
}
```

#### 생성된 페이지 목록 조회

```bash
curl http://localhost:4000/api/scaffold
```

#### 코드 미리보기

```bash
curl http://localhost:4000/api/scaffold/MNET010/preview
```

#### 페이지 삭제

```bash
curl -X DELETE http://localhost:4000/api/scaffold/MNET010
```

---

## 지원 페이지 타입

| 타입 | 설명 | 사용 템플릿 |
|---|---|---|
| `list-detail` | 좌측 검색+그리드 + 우측 상세 패널 (Splitter 분할) | `StandardListTemplate` + `StandardDetailTemplate` |
| `list` | 검색 폼 + 그리드 단독 (상세 패널 없음) | `StandardListTemplate` |
| `edit` | 독립적인 입력/수정 폼 화면 | `StandardEditTemplate` |
| `tab-detail` | 좌측 그리드 + 우측 탭형 상세 패널 | `StandardListTemplate` + `StandardTabTemplate` |

---

## 지원 필드 타입

| 타입 | 검색 컴포넌트 | 그리드 표시 | 상세/편집 컴포넌트 |
|---|---|---|---|
| `text` | `InputText` | 텍스트 | `InputText` |
| `number` | `InputNumber` | 숫자 | `InputNumber` |
| `select` | `Select` (드롭다운) | 표시명 텍스트 | `Select` |
| `badge` | `Select` (드롭다운) | `DotStatusText` | `DotStatusText` |
| `date` | `SingleDatePicker` | 날짜 문자열 | `SingleDatePicker` |
| `daterange` | `RangeDatePicker` | 날짜 문자열 | `RangeDatePicker` |
| `textarea` | 미지원 | - | `Textarea` |
| `radio` | `Select` | 표시명 텍스트 | `Select` |
| `checkbox` | 미지원 | boolean | checkbox |

---

## 생성 원리

### 1. LLM 창작 없는 템플릿 기반 생성

`VuePageGenerator.ts` 가 TypeScript 템플릿 리터럴로 완성된 Vue SFC 문자열을 조립.  
LLM 의 창의적 생성 없이, **필드 메타데이터 → 결정론적 코드 생성** 원칙을 따름.

### 2. ts-morph AST 기반 라우터 수정

`RouterUpdater.ts` 가 `ts-morph` 라이브러리로 `staticRoutes.ts` 의 AST 를 파싱.  
문자열 replace 없이 AST 노드를 직접 삽입하므로 기존 주석·포맷이 유지됨.

```
staticRoutes 배열
  └── 모든 기존 라우트
  └── [NotFound] ← 이 앞에 삽입
```

### 3. API 연동 없는 완전한 Mock 페이지

생성된 페이지에는:
- `MOCK_DATA` 상수 (20개 더미 row, 필드 타입에 맞는 한국어 데이터)
- 클라이언트 사이드 필터링 (computed + reactive searchParams)
- 클라이언트 사이드 페이지네이션 (computed + page.first/rows)

API 없이 즉시 동작하는 화면을 고객에게 공유 가능.

---

## 생성 후 실제 업무 화면으로 전환 방법

1. `src/pages/generated/{screenId}/index.vue` 를 `src/pages/{업무경로}/{screenId}/index.vue` 로 이동
2. `MOCK_DATA` 를 실제 API 호출 (`useQuery`, `axios` 등)로 교체
3. `filteredRows` computed 를 서버사이드 페이지네이션으로 교체
4. `staticRoutes.ts` 의 라우트 경로를 업무 경로로 수정
5. `scaffold-meta.json` 삭제

---

## 주의사항

- `scaffolding/` 서버는 **개발 환경 전용** 도구입니다. 프로덕션 빌드에 포함하지 마세요.
- `staticRoutes.ts` 파일이 AST 파싱 과정에서 자동 저장됩니다. git diff 로 변경 사항을 확인하세요.
- 동일한 `screenId` 로 재생성 시 파일이 덮어쓰기됩니다 (라우터는 중복 삽입되지 않음).
