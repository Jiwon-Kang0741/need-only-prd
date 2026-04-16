/**
 *
 * @param sub - 오늘 날짜에서 뺄 날짜 값
 * @param dateText - 요일 || 주 || 월 || 년
 */
export function datePickerDefaultValue(
  sub: number = 7,
  dateText: string = 'day'
) {
  const today = new Date();
  const preDate = new Date(today);
  today.setHours(0, 0, 0, 0);
  preDate.setHours(0, 0, 0, 0);

  switch (dateText) {
    case 'day':
      preDate.setDate(today.getDate() - sub);
      break;
    case 'week':
      preDate.setDate(today.getDate() - sub * 7);
      break;
    case 'month':
      preDate.setMonth(today.getMonth() - sub);
      break;
    case 'year':
      preDate.setFullYear(today.getFullYear() - sub);
      break;
    default:
      preDate.setDate(today.getDate() - sub);
      break;
  }

  return [preDate, today];
}
