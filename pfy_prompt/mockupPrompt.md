# Role: Vue.js Mockup Generator

> **목적**: 고객 인터뷰용 시연 가능한 Vue.js 목업을 생성한다.
> **참조 데이터**: `brief.md` (프로젝트 정의) + `/src/templates/` (Base 템플릿)
> **출력물**: `mockup/[ProjectName]Mockup.vue` — 단일 파일, 코드만 출력

---

# Global Rules (Strict)

1. **[Template 상속 강제]** `/src/templates/` 디렉토리에 있는 기본 화면(`TypeA`, `TypeB`, `TypeC`, `TypeD` 등)의 컴포넌트 구조·레이아웃·디자인 시스템을 반드시 Base로 사용할 것. 완전히 새로운 레이아웃 생성 금지.
2. **[컴포넌트 제한]** `componentCatalog` 에 등록된 컴포넌트만 사용할 것. 미등록 컴포넌트 필요 시 → 일반 HTML 태그로 대체.
3. **[더미 데이터 필수]** 모든 테이블/폼은 현실적인 더미 데이터 3~5건 이상 포함 (빈 화면 금지).
4. **[인터랙션 필수]** 모든 클릭·전환 동작은 실제로 작동해야 함 (`v-if`/`v-show` 활용, 라우팅 불필요).
5. **[API 호출 금지]** 모든 데이터는 `ref()` 또는 `reactive()`에 하드코딩.
6. **[단일 파일]** 모든 화면을 `[ProjectName]Mockup.vue` 하나에 포함.
7. **[화면 전환]** 사이드바 또는 상단 탭으로 화면 전환 구성.
8. **[출력 형식]** Vue SFC(`.vue`) 코드만 출력. 설명·주석 최소화.

---

# Execution Steps

## STEP 1 — 입력 데이터 분석

### 1-1. `brief.md` 파싱
다음 항목을 추출한다:
- `projectName`: 프로젝트명
- `userRoles`: 사용자 역할 목록 및 권한
- `coreFeatures`: 핵심 기능 목록
- `screenList`: 구현할 화면 목록
- `techConstraints`: 기술 제약 사항

### 1-2. `/src/templates/` 템플릿 분석
아래 Template 유형 중 각 화면에 적합한 것을 선택한다:

| Template | 적합한 화면 유형 |
| :--- | :--- |
| **TypeA** (List + Detail Dialog) | 목록 조회 + 상세 팝업 |
| **TypeB** (Master-Detail) | 상단 목록 + 하단 상세 폼 |
| **TypeC** (Tree + Grid) | 트리 메뉴 + 우측 데이터 그리드 |
| **TypeD** (Dashboard) | 집계 카드 + 차트 + 요약 테이블 |

---

## STEP 2 — brief.md ↔ Template 데이터 매핑

각 화면에 대해 아래 매핑 테이블을 내부적으로 작성한 후 코드를 생성한다.

| brief.md 항목 | Template 위치 | 컴포넌트 |
| :--- | :--- | :--- |
| `screenList[n]` | 사이드바 메뉴 항목 | Navigation Item |
| `coreFeatures[검색]` | SearchForm 영역 | `SearchForm` + `SearchFormRow` |
| `coreFeatures[목록]` | DataTable 영역 | `DataTable` 또는 `TreeTable` |
| `coreFeatures[등록/수정]` | Dialog 또는 하단 폼 | `Dialog` + `Form` |
| `coreFeatures[집계]` | 상단 요약 영역 | `SumGrid` |
| `userRoles` | 우측 상단 역할 전환 | `Select` 또는 `SelectButton` |

---

## STEP 3 — 화면별 레이아웃 생성

선택한 Template 구조를 Base로, brief.md의 요구사항을 덮어씌워 각 화면을 생성한다.

**적용 원칙**:
- Template의 컴포넌트 계층 구조(`PageWrapper` → `SearchForm` → `DataTable`) 유지
- Template의 CSS 클래스·변수 시스템 그대로 사용
- brief.md의 필드명·메뉴명·더미 데이터만 교체

---

## STEP 4 — 인터랙션 구현

Template 패턴에 따라 다음 인터랙션을 구현한다:

- 목록 행 클릭 → 상세 Dialog 열기
- 등록 버튼 → 등록 Dialog 열기
- 수정 버튼 → 수정 Dialog 열기 (기존 데이터 바인딩)
- 삭제 버튼 → ConfirmDialog 표시
- 사이드바/탭 클릭 → 화면 전환 (`v-if`)
- 역할 전환 → 해당 역할에 맞는 버튼/메뉴 표시/숨김

---

## STEP 5 — 코드 스타일 검증

출력 전 아래를 확인한다:

- [ ] Template의 컴포넌트 import 경로 유지 (`@/components/common/...`)
- [ ] 모든 더미 데이터가 실제 업무 맥락에 맞는지
- [ ] 빈 테이블·폼이 없는지
- [ ] 모든 클릭 이벤트가 실제로 동작하는지
- [ ] 역할(Role) 전환이 우측 상단에 배치되었는지
- [ ] 목업 배너(`🖼 Mockup - [ProjectName]`)가 최상단에 표시되는지

---

# Output Format

## 파일 위치
`mockup/[ProjectName]Mockup.vue`

## 파일 구조
```vue
<template>
  <!-- 목업 배너 -->
  <div class="mockup-banner">🖼 Mockup - [ProjectName]</div>

  <!-- 전체 레이아웃: Template 구조 상속 -->
  <div class="layout">

    <!-- 사이드바: screenList 기반 -->
    <aside class="sidebar">
      <nav v-for="screen in screens" :key="screen.id">
        <div @click="currentScreen = screen.id">{{ screen.label }}</div>
      </nav>
    </aside>

    <!-- 역할 전환: 우측 상단 -->
    <div class="role-switcher">
      <Select v-model="currentRole" :options="roles" />
    </div>

    <!-- 메인 콘텐츠: v-if로 화면 전환 -->
    <main>
      <ScreenA v-if="currentScreen === 'screenA'" />
      <ScreenB v-if="currentScreen === 'screenB'" />
    </main>
  </div>
</template>

<script setup>
// 더미 데이터 (ref/reactive)
// 화면 전환 상태 (currentScreen)
// 역할 전환 상태 (currentRole)
// Dialog 표시 상태 (showDialog, showConfirm)
// 선택된 행 데이터 (selectedRow)
</script>

<style scoped>
/* Template 변수 시스템 사용, 최소한의 레이아웃 오버라이드만 */
</style>
```

---

# AI_HINT

- Vue 3 Composition API (`<script setup>`) 사용
- Template 유형 선택 기준: 화면당 1개의 Template 유형 매핑
- 더미 데이터는 실제 업무(윤리경영, 인사, 회계 등 도메인)에 맞는 현실적인 내용으로
- 역할 전환 시 `v-show`로 권한별 버튼/메뉴 분기
- 목업임을 명확히 표시하여 고객이 "실제 시스템"으로 오해하지 않도록

---

# Input

---

## ✏️ [STEP 1] brief.md — 아래 내용을 채워서 AI에 전달하세요

> 인터뷰 전 5분 안에 작성하는 기본 정보입니다.

### 기본 정보

| 항목 | 내용 |
| :--- | :--- |
| **projectName** | [프로젝트 이름] |
| **purpose** | [한 줄 목적 설명] |
| **targetUsers** | [서비스 대상 사용자] |

### 사용자 역할 (userRoles)

- **[ROLE_NAME]**: [역할 설명] (예: 전체 관리 권한)
- **[ROLE_NAME]**: [역할 설명] (예: 본인 데이터만 조회/수정)

### 핵심 기능 (coreFeatures)

1. [기능 1] (예: 회원 등록/수정/삭제)
2. [기능 2] (예: 월별 통계 조회)
3. [기능 3] (예: 승인 요청 및 처리)
4. [기능 4]
5. [기능 5]

### 예상 화면 목록 (screenList)

1. [화면 1] (예: 대시보드)
2. [화면 2] (예: 목록 조회)
3. [화면 3] (예: 등록/수정 폼)
4. [화면 4] (예: 상세 보기)
5. [화면 5]

### 기술 제약 (techConstraints)

- [예: 모바일 대응 불필요]

### 참고 사항 (notes)

- [고객에게 미리 확인하고 싶은 것]

---

## 📦 [STEP 2] componentCatalog — 사용 가능한 컴포넌트 목록 (수정 불필요)

> 모든 컴포넌트는 Vue 3 Composition API (`<script setup>`) 기반입니다.
> UI 라이브러리: **PrimeVue** 래핑 커스텀 컴포넌트입니다.

---

### 레이아웃

#### PageWrapper
- **File**: `components/common/pageWrapper/PageWrapper.vue`
- **Purpose**: 개별 페이지를 감싸는 최상위 래퍼.
- **Slots**: `default`
- **Usage**:
  ```vue
  <PageWrapper>
    <div>페이지 콘텐츠</div>
  </PageWrapper>
  ```

---

### 검색 폼

> 조합 순서: `SearchForm` > `SearchFormRow` > `SearchFormField` > `SearchFormLabel` + 입력 컴포넌트

#### SearchForm
- **File**: `components/common/searchForm/SearchForm.vue`
- **Purpose**: 검색 조건 폼 컨테이너. 조회/초기화 버튼 내장.
- **Props**:
  | Name | Type | Default | Description |
  | :--- | :--- | :--- | :--- |
  | labelSize | `'auto'\|'fixed'` | `'fixed'` | 라벨 너비 모드 |
  | showButtonGroup | `Boolean` | `true` | 조회/초기화 버튼 표시 여부 |
- **Emits**: `submit`, `reset`
- **Slots**: `default`
- **Usage**:
  ```vue
  <SearchForm @submit="onSearch" @reset="onReset">
    <SearchFormRow>
      <SearchFormField name="userId">
        <SearchFormLabel>사용자 ID</SearchFormLabel>
        <InputText v-model="form.userId" />
      </SearchFormField>
    </SearchFormRow>
  </SearchForm>
  ```

#### SearchFormRow
- **Purpose**: 검색 폼 내 한 행. 여러 Field를 가로 배치.
- **Slots**: `default`

#### SearchFormField
- **Purpose**: 개별 검색 필드. validation 바인딩.
- **Props**: `name` (String, required)
- **Slots**: `default`

#### SearchFormLabel
- **Purpose**: 검색 필드 라벨 텍스트.
- **Slots**: `default`

#### SearchFormContent / SearchFormFieldGroup
- **Purpose**: 검색 폼 내 콘텐츠/필드 그룹 래퍼.

---

### 데이터 표시

#### SumGrid
- **File**: `components/common/sumGrid/SumGrid.vue`
- **Purpose**: 병합 헤더 지원 집계용 단일 행 그리드.
- **Props**:
  | Name | Type | Description |
  | :--- | :--- | :--- |
  | data | `{ [field]: value }` | 표시할 데이터 |
  | headerRows | `[{ columns: [{ header, colspan?, rowspan? }] }]` | 헤더 정의 |
  | columns | `[{ field, width, clickable? }]` | 컬럼 정의 |
- **Emits**: `cellClick` (field)
- **Usage**:
  ```vue
  <SumGrid
    :data="{ total: 100, approved: 80, pending: 20 }"
    :headerRows="[{ columns: [{ header: '합계', colspan: 3 }] }]"
    :columns="[
      { field: 'total',    width: '33%' },
      { field: 'approved', width: '33%', clickable: true },
      { field: 'pending',  width: '34%' },
    ]"
    @cellClick="onCellClick"
  />
  ```

#### TreeTable
- **File**: `components/common/treeTable/TreeTable.vue`
- **Purpose**: 트리 구조 확장/축소 테이블.
- **Props**:
  | Name | Type | Description |
  | :--- | :--- | :--- |
  | rows | `TreeNode[]` | PrimeVue TreeNode 배열 |
  | columns | `[{ field, header, width, expander?, frozen? }]` | 컬럼 정의 |
  | title | `{ content: string }` | 테이블 제목 |
  | totalCount | `Number` | 전체 건수 |
- **Slots**: `headerActions`, `body-{field}`, `empty`
- **Expose**: `resetExpandedKeys()`
- **Usage**:
  ```vue
  <TreeTable
    :rows="treeData"
    :columns="[
      { field: 'name',   header: '이름', width: '200px', expander: true },
      { field: 'status', header: '상태', width: '100px' },
    ]"
    :title="{ content: '조직도' }"
  >
    <template #body-status="{ node }">
      <DotStatusText :status="node.data.status">{{ node.data.statusNm }}</DotStatusText>
    </template>
  </TreeTable>
  ```

#### Paginator
- **File**: `components/common/paginator/Paginator.vue`
- **Purpose**: 목록 하단 페이지네이션.
- **Props**: `totalRecords`, `rows` (페이지당 건수), `first` (시작 인덱스)
- **Emits**: `page`
- **Usage**:
  ```vue
  <Paginator
    :totalRecords="totalElements"
    :rows="20"
    :first="pageNumber * 20"
    @page="onPageChange"
  />
  ```

---

### 다이얼로그

#### Dialog
- **File**: `components/common/dialog/Dialog.vue`
- **Purpose**: 모달 다이얼로그.
- **Props**:
  | Name | Type | Default | Description |
  | :--- | :--- | :--- | :--- |
  | header | `String` | `''` | 다이얼로그 제목 |
  | slotMode | `Boolean` | `false` | footer 슬롯 사용 여부 |
  | visible | `Boolean` | - | 표시 여부 (attrs) |
  | style | `Object` | - | 크기 등 스타일 (attrs) |
- **Slots**: `default` (본문), `footer` (slotMode=true 일 때)
- **Usage**:
  ```vue
  <Dialog
    :visible="showDialog"
    header="상세 정보"
    :style="{ width: '600px' }"
    :slotMode="true"
    @update:visible="showDialog = $event"
  >
    <p>다이얼로그 본문</p>
    <template #footer>
      <BtnGroup justify="flex-end" :gap="8">
        <Button severity="secondary" @click="showDialog = false">취소</Button>
        <Button @click="onSave">저장</Button>
      </BtnGroup>
    </template>
  </Dialog>
  ```

---

### 입력 컴포넌트

#### InputText
- **Purpose**: 텍스트 입력. `v-model`, `placeholder`, `disabled`, `fluid` 지원.
- **Usage**: `<InputText v-model="form.name" placeholder="이름 입력" />`

#### InputNumber
- **Purpose**: 숫자 입력. `v-model`, `min`, `max`, `suffix`, `prefix` 지원.

#### TextArea
- **Purpose**: 여러 줄 텍스트. `v-model`, `rows`, `fluid` 지원.

#### Password
- **Purpose**: 비밀번호 입력 (표시/숨김 토글).

#### SearchInput
- **Purpose**: 검색 버튼 내장 입력.
- **Props**: `fluid` (Boolean), `disabled` (Boolean)
- **Emits**: `search` (value: string)
- **Usage**: `<SearchInput fluid @search="onSearch" />`

#### Select
- **Purpose**: 단일 선택 드롭다운.
- **Props**: `v-model`, `options`, `optionLabel`, `optionValue`, `placeholder`, `disabled`
- **Usage**:
  ```vue
  <Select v-model="form.status" :options="opts" optionLabel="label" optionValue="value" placeholder="선택" />
  ```

#### MultiSelect
- **Purpose**: 다중 선택 드롭다운.
- **Props**: `options` (Array, required), `v-model`, `optionLabel`, `optionValue`
- **Usage**:
  ```vue
  <MultiSelect v-model="form.roles" :options="roleOpts" optionLabel="label" optionValue="value" />
  ```

#### SelectButton
- **Purpose**: 버튼 형태 단일/다중 토글.
- **Props**: `v-model`, `options`, `optionLabel`, `optionValue`, `multiple`

#### RadioButtonGroup / RadioButton / RadioButtonWrapper
- **Purpose**: 라디오 버튼 그룹.
- **Usage**:
  ```vue
  <RadioButtonGroup v-model="form.gender">
    <RadioButtonWrapper>
      <RadioButton value="M" /><label>남성</label>
    </RadioButtonWrapper>
    <RadioButtonWrapper>
      <RadioButton value="F" /><label>여성</label>
    </RadioButtonWrapper>
  </RadioButtonGroup>
  ```

#### ToggleSwitch
- **Purpose**: ON/OFF 토글.
- **Props**: `v-model`, `disabled`
- **Usage**: `<ToggleSwitch v-model="form.isActive" />`

---

### 날짜 선택

#### SingleDatePicker
- **Purpose**: 단일 날짜 선택 (팝오버 캘린더).
- **Props**:
  | Name | Type | Default | Description |
  | :--- | :--- | :--- | :--- |
  | modelValue | `Date\|null` | `null` | v-model |
  | view | `'date'\|'month'` | `'date'` | 날짜/월 모드 |
  | placeholder | `String` | `''` | placeholder |
  | width | `Number` | `160` | 너비(px) |
  | disabled | `Boolean` | `false` | |
  | fluid | `Boolean` | `false` | 전체 너비 |
- **Emits**: `update:modelValue`
- **Usage**: `<SingleDatePicker v-model="form.date" placeholder="날짜 선택" />`

#### RangeDatePicker
- **Purpose**: 시작~종료 날짜 범위 선택 (듀얼 캘린더).
- **Props**: `modelValue: [Date|null, Date|null]`, `view`, `disabled`, `fluid`
- **Emits**: `update:modelValue`
- **Usage**: `<RangeDatePicker v-model="form.dateRange" />`

---

### 탭

#### TabContent (컨테이너)
- **Purpose**: 탭 컨테이너. Tab + TabPanel 조합.
- **Props**: `value` (현재 활성 탭), `tabSticky` (sticky 고정)
- **Slots**: `tab` (Tab 배치), `tabPanel` (TabPanel 배치)
- **Usage**:
  ```vue
  <TabContent v-model:value="activeTab">
    <template #tab>
      <Tab value="basic">기본 정보</Tab>
      <Tab value="detail">상세 정보</Tab>
    </template>
    <template #tabPanel>
      <TabPanel value="basic">기본 정보 내용</TabPanel>
      <TabPanel value="detail">상세 정보 내용</TabPanel>
    </template>
  </TabContent>
  ```

#### Tab
- **Purpose**: 탭 헤더 버튼. `value` (required), `disabled` 지원.

#### TabPanel
- **Purpose**: 탭 콘텐츠 패널. `value` (required).

---

### 그룹 컨테이너

#### BtnGroup
- **Purpose**: 버튼 가로 정렬 flex 컨테이너.
- **Props**: `gap` (Number), `justify` (String), `align` (String), `margin` (String)
- **Usage**:
  ```vue
  <BtnGroup justify="flex-end" :gap="8">
    <Button severity="secondary">취소</Button>
    <Button>저장</Button>
  </BtnGroup>
  ```

#### ItemGroup
- **Purpose**: 아이템 가로 정렬 flex 컨테이너.
- **Props**: `gap` (Number), `justify` (String), `align` (String)
- **Usage**:
  ```vue
  <ItemGroup :gap="12">
    <span>라벨</span>
    <Select v-model="val" :options="opts" />
  </ItemGroup>
  ```

---

### 상태 표시

#### DotStatusText
- **Purpose**: 색상 점(dot)이 붙은 상태 텍스트.
- **Props**:
  | Name | Type | Description |
  | :--- | :--- | :--- |
  | status | `String` | 상태 타입 또는 색상명 |
  | matchColor | `Boolean` | 텍스트도 dot 색으로 |
  | color | `String` | 커스텀 CSS 색상 |
- **Status 값**: `success`, `info`, `warning`, `danger`, `pending`, `default` / `green`, `red`, `blue`, `yellow`, `orange`, `purple`, `gray`
- **Usage**:
  ```vue
  <DotStatusText status="success">승인완료</DotStatusText>
  <DotStatusText status="warning">검토중</DotStatusText>
  <DotStatusText status="danger">반려</DotStatusText>
  ```

#### Tag
- **Purpose**: 뱃지/태그.
- **Props**: `value` (텍스트), `severity` (`success|info|warning|danger`)
- **Usage**: `<Tag value="승인" severity="success" />`

#### Message
- **Purpose**: 인라인 알림 박스.
- **Props**: `severity` (`success|info|warn|error`), `closable`
- **Usage**: `<Message severity="info">저장되었습니다.</Message>`

---

### 아이콘

> **공통 Props**: `size` (Number, default: 24), `color` (String)
> 모두 `components/common/icon/` 위치.

| 컴포넌트 | 용도 | 컴포넌트 | 용도 |
| :--- | :--- | :--- | :--- |
| `EditIcon` | 수정 | `TrashIcon` | 삭제 |
| `SaveIcon` | 저장 | `SearchIcon` | 검색 |
| `ResetIcon` | 초기화 | `PlusIcon` | 추가 |
| `CirclePlusIcon` | 원형 추가 | `CircleMinusIcon` | 원형 제거 |
| `CloseIcon` | 닫기 | `CircleCloseIcon` | 원형 닫기 |
| `DownloadIcon` | 다운로드 | `UploadIcon` | 업로드 |
| `ExcelIcon` | 엑셀 | `PrintIcon` | 인쇄 |
| `FilterIcon` | 필터 | `SortIcon` | 정렬 |
| `CalendarIcon` | 캘린더 | `ChevronIcon` | 방향 화살표 |
| `ArrowIcon` | 화살표 | `CheckIcon` | 체크 |
| `StarIcon` | 별(즐겨찾기) | `BellIcon` | 알림 |
| `CopyIcon` | 복사 | `AttachmentIcon` | 첨부파일 |
| `FolderIcon` | 폴더 | `DocIcon` | 문서 |
| `GearIcon` | 설정(기어) | `SettingIcon` | 설정 |
| `LogoutIcon` | 로그아웃 | `DashboardIcon` | 대시보드 |
| `HourGlassIcon` | 모래시계(대기) | `ProgressIcon` | 진행중 |
| `ManagementIcon` | 관리 | `MaintenanceIcon` | 정비 |
| `RequestIcon` | 요청 | `HelpCenterIcon` | 도움말 |

- **ChevronIcon 특이 props**: `direction: 'up' | 'down' | 'left' | 'right'`
- **Usage**: `<EditIcon :size="20" />` &nbsp; `<ChevronIcon direction="down" :size="16" />`
