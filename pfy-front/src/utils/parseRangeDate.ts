import { formatDateToUtc } from '@/utils/formatDate';

type RequestDateValue =
  | string
  | [Date | null, Date | null]
  | Date
  | null
  | undefined;

type ParsedDateRange = {
  start: Date | null | string;
  end: Date | null | string;
};

const isValidDate = (date: unknown): date is Date =>
  date instanceof Date && !Number.isNaN(date.getTime());

export function parseRangeDate(requestDate: RequestDateValue): ParsedDateRange {
  if (typeof requestDate === 'string') {
    const trimmed = requestDate.trim();

    if (trimmed.includes(' - ')) {
      const [startStr, endStr] = trimmed.split(' - ');
      // const start = new Date(startStr.trim());
      // const end = new Date(endStr.trim());

      const start = formatDateToUtc(startStr.trim());
      const end = formatDateToUtc(endStr.trim());
      return {
        start,
        end,
      };
    }
  }

  if (Array.isArray(requestDate)) {
    const [start, end] = requestDate;
    return {
      start: isValidDate(start) ? formatDateToUtc(start) : null,
      end: isValidDate(end) ? formatDateToUtc(end, { endTime: true }) : null,
    };
  }

  return {
    start: null,
    end: null,
  };
}
