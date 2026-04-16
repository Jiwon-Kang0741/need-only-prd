import type { MasterData } from '../../../index.vue';

export function formatDate(value: string | null | undefined): string {
  if (!value || value.length !== 8) return value ?? '';
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
}

// NOTE: 마스터 테이블 컬럼을 실제 데이터에 맞게 수정하세요
export function getMasterColumns() {
  return [
    { field: 'ROW_NO',     header: 'No.',    style: 'width: 60px',      headerClass: 'center', bodyClass: 'center', frozen: true },
    { field: 'MASTER_KEY', header: '관리번호', style: 'min-width: 140px', frozen: true },
    { field: 'MASTER_NM',  header: '관리명',  style: 'min-width: 200px' },
    { field: 'STATUS_NM',  header: '상태',   style: 'min-width: 110px', headerClass: 'center', bodyClass: 'center' },
    { field: 'REG_DT_FORMATTED', header: '등록일', style: 'min-width: 120px', headerClass: 'center', bodyClass: 'center' },
    { field: 'REG_USER_NM', header: '등록자', style: 'min-width: 110px', headerClass: 'center', bodyClass: 'center' },
    { field: 'REMARK',     header: '비고',    style: 'min-width: 200px' },
  ];
}

export function getMasterRows(data: MasterData[]): MasterData[] {
  if (!Array.isArray(data)) return [];
  return data.map((row, index) => ({
    ...row,
    ROW_NO: index + 1,
    REG_DT_FORMATTED: formatDate(row.REG_DT),
  }));
}
