import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

import { FormatDateOptions } from '@/types/dateFormatOptions';

dayjs.extend(utc);

export function formatUtcDate(
  utcInput: string | Date,
  options: FormatDateOptions = {}
): string {
  const {
    locale = navigator.language || document.documentElement.lang || 'en-US',
    dateOnly = true,
    hour12 = true,
  } = options;
  const date = new Date(utcInput);

  let formatOptions: Intl.DateTimeFormatOptions;

  if (dateOnly) {
    formatOptions = {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
    };
  } else if (!dateOnly && hour12) {
    formatOptions = {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      // timeZoneName: 'short', 타임존 필요하면 추가
    };
  } else {
    formatOptions = {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      // timeZoneName: 'short', 타임존 필요하면 추가
    };
  }

  return new Intl.DateTimeFormat(locale, formatOptions).format(date);
}

function isValidDate(d: Date) {
  return d instanceof Date && !Number.isNaN(d.getTime());
}

/**
 * Date Picker 값 → 백엔드 전송용 UTC ISO 변환
 * - YYYY-MM-DD 문자열 → 로컬 하루(00:00/23:59:59) → UTC 변환
 * - Date 객체 → 로컬 하루(00:00/23:59:59) → UTC 변환
 */

export function formatDateToUtc(
  input: string | Date,
  options: FormatDateOptions = {}
): string {
  const { dateOnly = true, endTime = false } = options;

  const toUtcStringFromLocal = (d: Date): string => {
    const local = new Date(d);
    if (endTime) {
      local.setHours(23, 59, 59, 999);
    } else {
      local.setHours(0, 0, 0, 0);
    }
    return local.toISOString(); // 항상 UTC ISO 문자열
  };

  if (typeof input === 'string') {
    const trimmed = input.trim();
    // YYYY-MM-DD
    const pureDate = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
    if (pureDate) {
      return toUtcStringFromLocal(new Date(trimmed));
    }
    // ISO 문자열 → Date
    const parsed = new Date(trimmed);
    if (!isValidDate(parsed)) throw new Error('Invalid date string');
    return dateOnly ? toUtcStringFromLocal(parsed) : parsed.toISOString();
  }

  if (!isValidDate(input)) throw new Error('Invalid Date');
  return dateOnly ? toUtcStringFromLocal(input) : input.toISOString();
}

/**
 * 로컬 Date | string | dayjs 객체를 UTC ISO 문자열로 변환
 * @param date 입력값 (Date | string | dayjs)
 * @param formatIso ISO 형태 여부 (기본 true: `2025-08-17T06:00:00Z`)
 */
export function toUtcString(
  date: string | Date | dayjs.Dayjs,
  formatIso = true
): string {
  const d = dayjs(date).utc();
  return formatIso ? d.toISOString() : d.format('YYYY-MM-DD HH:mm:ss');
}

// YYYYMMDD 형식 문자열을 Date 객체로 변환
export function parseDateStringToUTC(yyyymmdd: string): Date | null {
  if (!/^\d{8}$/.test(yyyymmdd)) return null;
  const y = Number(yyyymmdd.slice(0, 4));
  const m = Number(yyyymmdd.slice(4, 6));
  const d = Number(yyyymmdd.slice(6, 8));

  const ms = Date.UTC(y, m - 1, d); // UTC 자정
  const date = new Date(ms);
  // 유효성 검증
  if (
    date.getUTCFullYear() !== y ||
    date.getUTCMonth() !== m - 1 ||
    date.getUTCDate() !== d
  ) {
    return null;
  }
  return date;
}

// YYYYMMDDHHmmSS 형식의 한국 시간을 UTC Date로 변환 (KST → UTC)
export function parseKoreanDateStringToUTC(
  yyyymmddHHmmSS: string
): Date | null {
  // 14자리 숫자인지 검증 (YYYYMMDDHHmmSS)
  if (!/^\d{14}$/.test(yyyymmddHHmmSS)) return null;

  // 날짜/시간 파싱
  const y = Number(yyyymmddHHmmSS.slice(0, 4));
  const m = Number(yyyymmddHHmmSS.slice(4, 6));
  const d = Number(yyyymmddHHmmSS.slice(6, 8));
  const h = Number(yyyymmddHHmmSS.slice(8, 10));
  const min = Number(yyyymmddHHmmSS.slice(10, 12));
  const s = Number(yyyymmddHHmmSS.slice(12, 14));

  // 한국 표준시(KST)는 UTC+9
  const KST_OFFSET = 9 * 60 * 60 * 1000; // 9시간을 밀리초로 변환

  // 한국 시간으로 Date 객체 생성 후 UTC로 변환
  const koreanTime = new Date(y, m - 1, d, h, min, s);
  const utcTime = koreanTime.getTime() - KST_OFFSET;
  const utcDate = new Date(utcTime);

  // 유효성 검증 (원래 한국 시간과 비교)
  const expectedKoreanTime = new Date(y, m - 1, d, h, min, s);
  if (expectedKoreanTime.getTime() !== koreanTime.getTime()) {
    return null;
  }

  return utcDate;
}

// datepicker가 던지는 값을 YYYYMMDD 형식 문자열로 변환
export function formatDateToYYYYMMDD(
  value: Date | string | number | null | undefined
): string {
  if (!value) return '';

  try {
    let date: Date;

    // 입력값을 Date 객체로 변환
    if (typeof value === 'number') {
      date = new Date(value);
    } else if (typeof value === 'string') {
      const trimmed = value.trim();

      // 다양한 날짜 형식을 직접 처리 (가장 효율적)
      // YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD 형식
      const datePattern = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/.exec(trimmed);
      if (datePattern) {
        const [, y, m, d] = datePattern;
        const month = m.padStart(2, '0');
        const day = d.padStart(2, '0');
        return `${y}${month}${day}`;
      }

      // YYYYMMDD 형식 (이미 완성된 형태)
      if (/^\d{8}$/.test(trimmed)) {
        return trimmed;
      }

      date = new Date(trimmed);
    } else {
      date = value;
    }

    // 유효한 날짜인지 확인
    if (!isValidDate(date)) return '';

    // 로컬 달력 날짜를 기준으로 YYYYMMDD 생성 (UTC 변환 없이)
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
  } catch {
    return '';
  }
}

// 한국 고정
export function formatUtcDateKo(
  utcInput: string | Date,
  options: FormatDateOptions = {}
): string {
  const { locale = 'ko-KR', dateOnly = true, hour12 = true } = options;
  const date = new Date(utcInput);

  let formatOptions: Intl.DateTimeFormatOptions;

  if (dateOnly) {
    formatOptions = {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
    };
  } else if (!dateOnly && hour12) {
    formatOptions = {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      // timeZoneName: 'short', 타임존 필요하면 추가
    };
  } else {
    formatOptions = {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      // timeZoneName: 'short', 타임존 필요하면 추가
    };
  }

  return new Intl.DateTimeFormat(locale, {
    ...formatOptions,
    timeZone: 'Asia/Seoul',
  }).format(date);
}

/**
 * YYYYMMDD 형식 문자열을 YYYY-MM-DD 형식으로 변환
 * @param yyyymmdd YYYYMMDD 형식 문자열 (예: "20231215")
 * @returns YYYY-MM-DD 형식 문자열 (예: "2023-12-15")
 */
export function formatYYYYMMDDToDisplay(yyyymmdd: string): string {
  if (!yyyymmdd) return '';

  let dateStr = yyyymmdd;

  // YYYYMMDD 형식인지 확인 (8자리 숫자)
  if (!/^\d{8}$/.test(dateStr)) {
    // YYYYMMDDHHmmss 형식 (14자리)인 경우 앞 8자리만 사용
    if (/^\d{14}$/.test(dateStr)) {
      dateStr = dateStr.slice(0, 8);
    } else {
      return dateStr; // 그 외의 경우 그대로 반환
    }
  }

  return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
}

/**
 * Date 객체를 지정된 포맷으로 변환
 * @param value Date 객체 또는 날짜 문자열
 * @param type 변환 타입 (현재 'Date'만 지원)
 * @param format 출력 포맷 ('YYYYMMDD' 지원)
 */
export function formatDateToString(
  value: Date | string | null | undefined,
  type: string,
  format: string
): string {
  if (!value) return '';

  try {
    let date: Date;

    if (value instanceof Date) {
      date = value;
    } else if (typeof value === 'string') {
      date = new Date(value);
    } else {
      return '';
    }

    // 유효한 날짜인지 확인
    if (!isValidDate(date)) return '';

    if (format === 'YYYYMMDD') {
      // 로컬 달력 날짜를 기준으로 YYYYMMDD 생성
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}${month}${day}`;
    }

    return '';
  } catch {
    return '';
  }
}
