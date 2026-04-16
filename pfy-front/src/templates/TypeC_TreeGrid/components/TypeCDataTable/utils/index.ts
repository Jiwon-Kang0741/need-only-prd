import type { MainData } from '../../../types';

export function formatDate(value: string | null | undefined): string {
  if (!value || value.length !== 8) return value ?? '';
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
}

export function getColumns() {
  return [
    { field: 'ROW_NO',     header: 'No.',   style: 'width: 60px',      headerClass: 'center', bodyClass: 'center', frozen: true },
    { field: 'ITEM_NO',    header: '항목번호', style: 'min-width: 140px', frozen: true },
    { field: 'ITEM_NM',    header: '항목명',  style: 'min-width: 200px' },
    { field: 'STATUS_NM',  header: '상태',   style: 'min-width: 110px', headerClass: 'center', bodyClass: 'center' },
    { field: 'REG_DT_FORMATTED', header: '등록일', style: 'min-width: 120px', headerClass: 'center', bodyClass: 'center' },
    { field: 'REG_USER_NM', header: '등록자', style: 'min-width: 110px', headerClass: 'center', bodyClass: 'center' },
  ];
}

export function getRows(data: MainData[]): MainData[] {
  if (!Array.isArray(data)) return [];
  return data.map((row, index) => ({
    ...row,
    ROW_NO: index + 1,
    REG_DT_FORMATTED: formatDate(row.REG_DT),
    REG_USER_NM: row.REG_USER_NM ?? row.REG_NM ?? '',
  }));
}
