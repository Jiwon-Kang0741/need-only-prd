// ─────────────────────────────────────────────────────────────────────────────
//  Scaffolding System — Shared Type Definitions
// ─────────────────────────────────────────────────────────────────────────────

/** 생성할 페이지 레이아웃 종류 */
export type PageType = 'list-detail' | 'list' | 'edit' | 'tab-detail';

/** 필드 데이터 타입 */
export type FieldType =
  | 'text'
  | 'number'
  | 'select'
  | 'radio'
  | 'badge'       // select + 색상 표시 (DotStatusText)
  | 'date'
  | 'daterange'
  | 'textarea'
  | 'checkbox';

/** select / radio / badge 필드의 옵션 항목 */
export interface FieldOption {
  label: string;
  value: string;
  /** badge 타입에서 DotStatusText 색상 */
  color?: string;
}

/** 화면 필드 하나를 기술하는 메타데이터 */
export interface FieldDef {
  /** camelCase 키 이름. 예: "reportType" */
  key: string;
  /** 화면 표시 레이블. 예: "신고유형" */
  label: string;
  type: FieldType;
  /** 검색 폼에 포함 여부 */
  searchable?: boolean;
  /** 그리드 컬럼으로 표시 여부 */
  listable?: boolean;
  /** 상세 패널/화면에 표시 여부 */
  detailable?: boolean;
  /** 입력/수정 폼에 포함 여부 */
  editable?: boolean;
  /** 입력 폼에서 필수 항목 여부 */
  required?: boolean;
  /** select / radio / badge 선택지 */
  options?: FieldOption[];
  /** 그리드 컬럼 고정 너비. 예: "120px" */
  width?: string;
}

/** tab-detail 타입에서 탭 하나의 정의 */
export interface TabDef {
  /** 슬롯 이름 키. 예: "basic" → #panel-basic */
  key: string;
  /** 탭 버튼 레이블 */
  label: string;
  /** 이 탭에 표시할 필드들 */
  fields: FieldDef[];
}

/** 스캐폴딩 요청 전체 스펙 */
export interface ScaffoldRequest {
  /** 대문자 화면 ID. 예: "MNET010" — 라우트 이름 및 디렉터리 이름으로 사용 */
  screenId: string;
  /** 화면 한글 이름. 예: "신고 관리" */
  screenName: string;
  /** 메뉴 경로 (ContentHeader 브레드크럼 용도) */
  menuPath?: string[];
  pageType: PageType;
  /** list / list-detail / edit 타입에서 사용하는 필드 목록 */
  fields: FieldDef[];
  /** tab-detail 타입에서 탭별 필드 목록 */
  tabs?: TabDef[];
}

/** 스캐폴딩 결과 */
export interface ScaffoldResult {
  success: boolean;
  message: string;
  /** 생성된 .vue 파일의 절대 경로 */
  filePath?: string;
  /** 브라우저 접근 URL. 예: "/MNET010" */
  routePath?: string;
  /** 생성된 코드 미리보기 */
  preview?: string;
}

/** 이미 생성된 페이지 정보 */
export interface GeneratedPageInfo {
  screenId: string;
  screenName: string;
  pageType: PageType;
  routePath: string;
  generatedAt: string;
}
