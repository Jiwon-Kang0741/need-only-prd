export type UtilOptions =
  | 'addRow'
  | 'deleteRow'
  | 'copyInsertRow'
  | 'filter'
  | 'settings'
  | 'uploadExcel'
  | 'downloadExcel'
  | 'downloadTemplate'
  | 'reset';

export interface Column {
  objectId: string;
  field: string;
  header: string;
  width?: string;
  columnClass?: string;
  rowClass?: string;
  visible?: boolean;
  frozen?: boolean;
  tooltip?: string;
  editNewOnly?: boolean; // 새로운 행만 수정 가능
  required?: boolean; // 필수값
}
export type RowValues = Record<string, any>;
export type RowValuesInput = RowValues | RowValues[];

// Props
export type TitleProp =
  | {
      objectId?: string | '';
      content: string;
    }
  | string;

export type BodyActionsProp = {
  header: string;
  width: string;
  columnClass: string;
  rowClass: string;
} | null;

export type TableColumn = {
  objectId: string;
  field: string;
  header: string;
  width?: string;
  columnClass?: string;
  rowClass?: string;
  visible?: boolean;
  frozen?: boolean;
  required?: boolean;
  useRenderedValue?: boolean;
};
export interface DataTableProps {
  value: any[];
  dataKey: string;
  columns: TableColumn[];
  enableRowCheck?: boolean | { width?: string }; // 행 체크 기능 활성화 여부와 width 값을 통해 컬럼 너비 조정
  tableObjectName?: string; // title, 엑셀 다운로드 등의 추출 기능을 위해 등록
  checkedDatakeyList?: string[]; // 외부에서 체크박스를 관리하기 위한 props
  searchConditions?: { label: string; value: string }[];
  reorderableRows?: boolean; // 컬럼 재배치 기능 활성화 여부
  enableContextMenu?: boolean; // 컨텍스트 메뉴 활성화 여부 (기본값 true)
  title?: TitleProp; // 테이블 제목과 object id 설정
  showIndexColumns?: boolean | { header?: string; width?: string }; // 인덱스 컬럼 표시 여부와 header와 width 값을 통해 컬럼 내용, 너비 조정
  utilOptions?: UtilOptions[]; // 유틸리티 옵션
  totalCount?: number; // 총 행 수 (페이징 기능 사용 시 외부에서 주입하기 위한 props)
  columnDefaultValues?: Record<string, any>; // 행 추가 시 컬럼별 기본값
  bodyActions?: BodyActionsProp; // 액션 필드 사용 시 컬럼 설정
  showStatusColumn?: boolean; // 상태 컬럼 표시 여부
  copyInsertOptions?: {
    // 기본적으로는 editor 슬롯이 있는 필드들만 복사 붙여넣는 대상이지만 필요한 경우 복사 데이터를 추가하거나 제외할 수 있는 props
    includeFields?: string[];
    excludeFields?: string[];
  };
  downloadTemplateInfo?: {
    // 엑셀 템플릿 다운로드 시 필요한 정보
    bizCode: string; // 업무 코드
    windowId: string; // 윈도우 아이디
    inptSeqNo: number; // 입력 순번
  };
  confirmBeforeDeleteRow?: () => Promise<boolean>; // 행 삭제 시 커스텀 컨펌 로직이 필요할 때 사용
  onBeforeDownloadExcel?: () => Promise<any[]>; // 엑셀 다운로드 전 커스텀 로직을 띄우고 싶을 때 사용(페이징된 데이터의 엑셀 다운로드나, 데이터 변환을 위해 사용)
  customAddRow?: () => void; // 행 추가 시 커스텀 로직을 띄우고 싶을 때 사용
  onClickExcelUpload?: () => void; // 엑셀 업로드 시 커스텀 로직을 띄우고 싶을 때 사용
  onClickDownloadTemplate?: () => Promise<any[]>; // 엑셀 템플릿 다운로드 시 커스텀 로직을 띄우고 싶을 때 사용
  virtualScrollerOptions?: { itemSize?: number; [key: string]: any }; // 가상 스크롤링 옵션 (대용량 데이터 성능 최적화)
}
