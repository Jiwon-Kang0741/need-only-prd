type RequestDateValue = string | Date | null | undefined;

const isValidDate = (date: unknown): date is Date =>
  date instanceof Date && !Number.isNaN(date.getTime());

/**
 * 단일 날짜 문자열 또는 Date 객체를 안전하게 파싱
 */
export function parseSingleDate(input: RequestDateValue): Date | null {
  if (typeof input === 'string') {
    const trimmed = input.trim();
    // ISO 형식 또는 YYYY-MM-DD일 경우 Date 객체로 변환
    const parsed = new Date(trimmed);
    return isValidDate(parsed) ? parsed : null;
  }

  if (input instanceof Date) {
    return isValidDate(input) ? input : null;
  }

  return null;
}
