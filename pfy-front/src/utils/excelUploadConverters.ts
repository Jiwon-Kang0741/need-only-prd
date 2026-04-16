import type { Converter } from '@/utils/excelUpLoad';
import { formatDateToUtc } from '@/utils/formatDate';

import { excelSerialToDate, makeConvError } from './excelUpLoad';

/** 공통 문자열 컨버터: 공백 트림, 빈값 → null */
export const str: Converter<string> = (v) => {
  if (v == null || v === '') return null;
  return String(v).trim();
};

/** 공통 정수 컨버터: "1,234" 허용, 소수점/NaN/Infinity 거부 */
export const intOnly: Converter<number> = (v) => {
  if (v == null || v === '') return null;
  const s = String(v).replace(/,/g, '').trim();
  const n = Number(s);
  if (!Number.isFinite(n) || !Number.isInteger(n)) {
    throw makeConvError('NUMERIC');
  }
  return n;
};

/** 공통 실수 컨버터: "1,234.56" 허용, NaN/Infinity 거부 */
export const decimalOnly: Converter<number> = (v) => {
  if (v == null || v === '') return null;
  const s = String(v).replace(/,/g, '').trim();
  const n = Number(s);
  if (!Number.isFinite(n)) {
    throw makeConvError('NUMERIC');
  }
  return n;
};

/** 공통 Y/N 컨버터 */
export const yn: Converter<string> = (v) => {
  if (v === null || v === '' || typeof v === 'undefined') return 'N';
  const s = String(v).trim().toUpperCase();
  if (s === 'Y' || s === 'YES' || s === 'TRUE' || s === '1') return 'Y';
  if (s === 'N' || s === 'NO' || s === 'FALSE' || s === '0') return 'N';
  throw makeConvError('BOOLEAN', '');
};

type Order = 'YMD' | 'DMY' | 'MDY' | 'auto';

export interface DateParseOptions {
  /** 우선순위/기본 파싱 순서 (auto 권장) */
  preferOrder?: Order;
  /** 2자리 연도의 pivot 기준 (예: 1950 ⇒ 50~99는 19xx, 00~49는 20xx) */
  pivotYear?: number; // default 1950
  /** 허용 연도 범위(선택) */
  minYear?: number;
  maxYear?: number;
  /** YYYYMMDD(8자리) 무구분 문자열의 해석 순서 (기본 YMD) */
  compactOrder?: 'YMD' | 'DMY' | 'MDY';
}

const DEFAULT_OPTS: Required<
  Pick<DateParseOptions, 'preferOrder' | 'pivotYear' | 'compactOrder'>
> = {
  preferOrder: 'auto',
  pivotYear: 1950,
  compactOrder: 'YMD',
};

function normalizeInput(raw: string): string {
  // 1) trim
  let s = raw.trim();

  // 2) 유니코드 하이픈들을 ASCII '-'로 정규화
  s = s.replace(/[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]/g, '-');

  // 3) 한국식 접미사/다른 구분자 통일
  s = s
    .replace(/[./]/g, '-') // 점/슬래시 → 하이픈
    .replace(/\s+/g, '-') // 다중 공백 → 하이픈
    .replace(/\s*년\s*/g, '-') // "YYYY년"
    .replace(/\s*월\s*/g, '-') // "MM월"
    .replace(/\s*일\s*/g, ''); // "DD일"

  // 4) ISO DateTime이면 앞의 YYYY-MM-DD만 취함
  const isoLike = s.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoLike) [, s] = isoLike; // 구조 분해 할당

  return s;
}

function toFourDigitYear(token: number, pivotYear: number): number {
  // 2자리 연도 처리: [pivotYear..pivotYear+99] ↔ [pivotYear..pivotYear+49]는 20xx로 보정
  if (token >= 100) return token;
  const pivotYY = pivotYear % 100; // 예: 1950 → 50
  return token >= pivotYY ? 1900 + token : 2000 + token;
}

function tryBuildDate(
  y: number,
  m: number,
  d: number,
  bounds?: Pick<DateParseOptions, 'minYear' | 'maxYear'>
): Date | null {
  if (!Number.isInteger(y) || !Number.isInteger(m) || !Number.isInteger(d))
    return null;
  if (m < 1 || m > 12) return null;
  if (d < 1 || d > 31) return null;

  if (bounds?.minYear && y < bounds.minYear) return null;
  if (bounds?.maxYear && y > bounds.maxYear) return null;

  const dt = new Date(Date.UTC(y, m - 1, d));
  if (
    dt.getUTCFullYear() !== y ||
    dt.getUTCMonth() !== m - 1 ||
    dt.getUTCDate() !== d
  )
    return null;

  return dt;
}

function parseByOrder(
  parts: number[],
  order: Exclude<Order, 'auto'>,
  pivotYear: number,
  bounds?: Pick<DateParseOptions, 'minYear' | 'maxYear'>
): Date | null {
  let y: number;
  let m: number;
  let d: number;

  if (order === 'YMD') {
    [y, m, d] = parts;
    if (y < 100) y = toFourDigitYear(y, pivotYear);
  } else if (order === 'DMY') {
    [d, m, y] = parts;
    if (y < 100) y = toFourDigitYear(y, pivotYear);
  } else {
    // 'MDY'
    [m, d, y] = parts;
    if (y < 100) y = toFourDigitYear(y, pivotYear);
  }

  return tryBuildDate(y, m, d, bounds) ?? null;
}

/** 숫자 토큰 기반 자동 추론 로직 */
function autoDetect(
  parts: number[],
  sep: string,
  pivotYear: number,
  preferFallback: Exclude<Order, 'auto'>,
  bounds?: Pick<DateParseOptions, 'minYear' | 'maxYear'>
): Date | null {
  // 힌트1: 첫 토큰이 4자리 연도면 YMD
  if (String(parts[0]).length === 4) {
    const dt = parseByOrder(parts, 'YMD', pivotYear, bounds);
    if (dt) return dt;
  }

  // 힌트2: 마지막 토큰이 4자리면 보통 DMY/MDY
  if (String(parts[2]).length === 4) {
    // '.'를 많이 쓰면 유럽권 D.M.Y 경향 → DMY 우선
    if (sep === '.') {
      const dt =
        parseByOrder(parts, 'DMY', pivotYear, bounds) ||
        parseByOrder(parts, 'MDY', pivotYear, bounds);
      if (dt) return dt;
    } else {
      // 구분자만으로 확신 못 하면 값 기반으로 판별
      // month 후보는 1..12 안쪽이어야 함
      const [a, b] = parts;
      if (a > 12 && b <= 12) {
        const dt = parseByOrder(parts, 'DMY', pivotYear, bounds);
        if (dt) return dt;
      }
      if (a <= 12 && b > 12) {
        const dt = parseByOrder(parts, 'MDY', pivotYear, bounds);
        if (dt) return dt;
      }
      // 둘 다 1..12 면 애매 → preferFallback
      const dt = parseByOrder(parts, preferFallback, pivotYear, bounds);
      if (dt) return dt;
    }
  }

  // 힌트3: 값 기반 판별
  const [a, b, c] = parts;

  // a>12 → a는 day ⇒ DMY 시도
  if (a > 12) {
    const dt = parseByOrder(parts, 'DMY', pivotYear, bounds);
    if (dt) return dt;
  }
  // b>12 → b는 day ⇒ MDY 시도
  if (b > 12) {
    const dt = parseByOrder(parts, 'MDY', pivotYear, bounds);
    if (dt) return dt;
  }
  // c>31 이면 c가 연도 후보 → DMY/MDY 중 하나
  if (c > 31) {
    const dt =
      parseByOrder(parts, 'DMY', pivotYear, bounds) ||
      parseByOrder(parts, 'MDY', pivotYear, bounds);
    if (dt) return dt;
  }

  // 끝까지 모호하면 fallback
  return parseByOrder(parts, preferFallback, pivotYear, bounds);
}

/** 옵션형 범용 날짜 컨버터 팩토리 */
export function makeDateStr(options?: DateParseOptions): Converter<string> {
  const opts = { ...DEFAULT_OPTS, ...(options ?? {}) };

  return (v) => {
    if (v == null || v === '') return null;

    let dt: Date | null = null;

    if (v instanceof Date) {
      dt = v;
    } else if (typeof v === 'number' && Number.isFinite(v)) {
      // Excel serial
      dt = excelSerialToDate(v);
    } else if (typeof v === 'string') {
      const s = normalizeInput(v);

      // 8자리 무구분 숫자 (기본 YMD, 옵션으로 변경 가능)
      if (/^\d{8}$/.test(s)) {
        const a = Number(s.slice(0, 2));
        const b = Number(s.slice(2, 4));
        const c4 = Number(s.slice(4, 8));
        const a4 = Number(s.slice(0, 4));
        const b2 = Number(s.slice(4, 6));
        const c2 = Number(s.slice(6, 8));

        // compactOrder에 맞춰 parts 구성
        if (opts.compactOrder === 'YMD') {
          const parts = [a4, b2, c2];
          dt = parseByOrder(parts, 'YMD', opts.pivotYear, opts);
        } else if (opts.compactOrder === 'DMY') {
          const parts = [a, b, c4];
          dt = parseByOrder(parts, 'DMY', opts.pivotYear, opts);
        } else {
          // 'MDY'
          const parts = [a, b, c4];
          dt = parseByOrder(parts, 'MDY', opts.pivotYear, opts);
        }

        if (!dt) throw makeConvError('DATE');
      } else {
        // 구분자 분해
        const sepMatch = s.match(/[-]/);
        const sep = sepMatch ? '-' : ''; // 위에서 대부분 '-'로 통일했음
        const partsStr = s.split('-').filter(Boolean);
        if (partsStr.length !== 3) {
          throw makeConvError('DATE');
        }

        // 숫자만 남기기(앞에 0 허용), 숫자 외 문자가 섞여있으면 실패
        if (!partsStr.every((p) => /^\d+$/.test(p))) {
          throw makeConvError('DATE');
        }

        const partsNum = partsStr.map(Number);

        if (opts.preferOrder === 'auto') {
          dt = autoDetect(partsNum, sep || '-', opts.pivotYear, 'YMD', opts);
        } else {
          dt = parseByOrder(partsNum, opts.preferOrder, opts.pivotYear, opts);
        }

        if (!dt)
          throw makeConvError('DATE', '존재하지 않는 날짜입니다', {
            raw: v,
            norm: s,
          });
      }
    } else {
      throw makeConvError('DATE', '지원되지 않는 날짜 입력', { raw: v });
    }

    return formatDateToUtc(dt);
  };
}

/** 프로젝트 기본값으로 만든 범용 컨버터 (auto 추론 + pivot 1950) */
export const dateStr: Converter<string> = makeDateStr({
  preferOrder: 'auto',
  pivotYear: 1950,
  compactOrder: 'YMD', // 8자리 무구분은 YMD로 해석(20251021)
  // 필요하면 minYear/maxYear도 지정 가능
  // minYear: 1900,
  // maxYear: 2100,
});

/** 공통 날짜 컨버터: 다양한 구분자/ISO를 허용하고 UTC ISO로 반환 */
// export const dateStr: Converter<string> = (v) => {
//   if (v == null || v === '') return null;

//   let dt: Date;

//   if (v instanceof Date) {
//     dt = v;
//   } else if (typeof v === 'number' && Number.isFinite(v)) {
//     dt = excelSerialToDate(v);
//   } else if (typeof v === 'string') {
//     // 1) 트림
//     let s = v.trim();

//     // 2) 유니코드 하이픈들을 ASCII '-'로 정규화
//     s = s.replace(/[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]/g, '-');

//     // 3) 슬래시/점 및 "YYYY년 MM월 DD일"도 '-'로 통일
//     s = s
//       .replace(/[./]/g, '-')
//       .replace(/\s*년\s*/g, '-')
//       .replace(/\s*월\s*/g, '-')
//       .replace(/\s*일\s*/g, '');

//     // 4) ISO DateTime이면 앞의 YYYY-MM-DD만 추출 (구조 분해)
//     const isoLike = s.match(/^(\d{4}-\d{2}-\d{2})/);
//     if (isoLike) [, s] = isoLike;

//     // 5) 'YYYYMMDD'도 허용 → 'YYYY-MM-DD'로 변환
//     if (/^\d{8}$/.test(s)) {
//       s = `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
//     }

//     // 6) 최종 형식 검증
//     const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
//     if (!m) throw makeConvError('DATE');

//     const y = Number(m[1]);
//     const mo = Number(m[2]);
//     const d = Number(m[3]);

//     if (!Number.isInteger(y) || !Number.isInteger(mo) || !Number.isInteger(d)) {
//       throw makeConvError('DATE');
//     }

//     // 7) UTC 날짜 구성 + 역검증
//     dt = new Date(Date.UTC(y, mo - 1, d));
//     if (
//       dt.getUTCFullYear() !== y ||
//       dt.getUTCMonth() !== mo - 1 ||
//       dt.getUTCDate() !== d
//     ) {
//       throw makeConvError('DATE');
//     }
//   } else {
//     throw makeConvError('DATE');
//   }

//   return formatDateToUtc(dt);
// };

export const excelConverters = {
  str,
  intOnly,
  decimalOnly,
  yn,
  dateStr,
};
