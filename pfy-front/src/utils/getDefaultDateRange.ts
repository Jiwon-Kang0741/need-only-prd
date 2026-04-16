type Unit = 'day' | 'month' | 'year';

/**
 * 기준일을 기준으로 from ~ 기준일까지의 날짜 범위를 반환합니다.
 * @param n 기준일로부터 이전 범위 수 (예: 1달 전 → 1)
 * @param unit 'day' | 'month' | 'year'
 * @param baseDate 기준일 (기본값: 오늘)
 * @returns [startDate: Date, endDate: Date]
 */
export function getDefaultDateRange(
  n: number,
  unit: Unit = 'month',
  baseDate: Date = new Date()
): [Date, Date] {
  const end = new Date(baseDate);
  const start = new Date(baseDate);

  switch (unit) {
    case 'day':
      start.setDate(start.getDate() - n);
      break;
    case 'month':
      start.setMonth(start.getMonth() - n);
      break;
    case 'year':
      start.setFullYear(start.getFullYear() - n);
      break;
    default:
      start.setMonth(start.getMonth() - n);
      break;
  }

  return [start, end];
}
