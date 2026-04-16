import { getMsgNm } from '@/composables/useMessage';

export type Required =
  | string
  | { field: string; label?: string; validate?: (v: any, row: any) => boolean };

// 빈값 판별
const isEmptyValue = (v: any) => {
  if (v === null || v === undefined) return true;
  if (typeof v === 'string') return v.trim() === '';
  if (Array.isArray(v)) return v.length === 0;
  if (v instanceof Date) return Number.isNaN(v.getTime());
  if (typeof v === 'number') return Number.isNaN(v);
  return false;
};

// 'a.b.c' 경로 접근
const getByPath = (obj: any, path: string) =>
  path.split('.').reduce((acc, k) => (acc == null ? acc : acc[k]), obj);

/**
 * rows가 비어있으면: "변경 사항이 없습니다." 토스트 후 false
 * required가 없거나 빈 배열이면: 필드 검증 생략, true
 * required가 있으면: 첫 오류에서 토스트 1회 후 false, 모두 통과 시 true
 * rowStatus === 'D' (삭제 행)은 검증 대상에서 제외
 */
export async function validateRequiredFields(
  toast: (options: any) => void,
  rows: any[] = [],
  required?: Required[],
  options: { errorMessage?: string } = {}
): Promise<boolean> {
  // 변경 사항 없음
  if (!rows || rows.length === 0) {
    toast({
      severity: 'error',
      summary: 'Error',
      detail: await getMsgNm('CM0051'),
    });
    return false;
  }

  // 필수값 정의 없음
  if (!required || required.length === 0) {
    return true;
  }

  const reqs = required.map((r) =>
    typeof r === 'string'
      ? { field: r, label: undefined, validate: undefined }
      : r
  );

  for (let rowIndex = 0; rowIndex < rows.length; rowIndex += 1) {
    const row = rows[rowIndex];

    const status = String(row?.rowStatus ?? '')
      .trim()
      .toUpperCase();

    // 삭제된 행이 아니면 검증
    if (status !== 'D') {
      for (let j = 0; j < reqs.length; j += 1) {
        const { field, label, validate } = reqs[j]!;
        const value = getByPath(row, field);
        const invalid = validate ? !validate(value, row) : isEmptyValue(value);

        if (invalid) {
          // eslint-disable-next-line no-await-in-loop
          const errorDetail = await getMsgNm('VM0005', [label ?? field]);

          toast({
            severity: 'error',
            summary: 'Error',
            detail: options.errorMessage ?? errorDetail,
          });
          return false;
        }
      }
    }
  }

  return true;
}
