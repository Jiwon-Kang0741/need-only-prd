import { ref } from 'vue';
import * as XLSX from 'xlsx';

/* =================================
 * Types
 * ================================= */

export type StringKeyOf<T> = Extract<keyof T, string>;
export type HeaderMap<Row> = Record<string, StringKeyOf<Row>>; // "엑셀 헤더" → Row 키
export type Converter<T = unknown> = (cell: any) => T | null;

type WarningCode =
  | 'MISSING_HEADERS'
  | 'CONVERTER_ERROR'
  | 'EMPTY_FILE'
  | 'EMPTY_SHEET'
  | 'SHEET_NOT_FOUND'
  | 'TRUNCATED_ROWS'
  | 'NO_DATA_AFTER_HEADER';

export enum ExcelWarningCode {
  MISSING_HEADERS = 'MISSING_HEADERS',
  CONVERTER_ERROR = 'CONVERTER_ERROR',
  EMPTY_FILE = 'EMPTY_FILE',
  EMPTY_SHEET = 'EMPTY_SHEET',
  SHEET_NOT_FOUND = 'SHEET_NOT_FOUND',
  TRUNCATED_ROWS = 'TRUNCATED_ROWS',
  INVALID_FILE_FORMAT = 'INVALID_FILE_FORMAT',
  NO_DATA_AFTER_HEADER = 'NO_DATA_AFTER_HEADER',
}

export interface ParseOptions<Row> {
  /** Excel 헤더 → Row 키 매핑 (필수) */
  headerMap?: HeaderMap<Row>;
  /** 각 필드별 변환기 */
  converters?: Partial<Record<StringKeyOf<Row>, Converter>>;
  /** 전부 빈행이면 스킵 (기본 true) */
  skipAllEmptyRow?: boolean;
  /** 헤더가 위치한 행 (1-based). 지정 시 자동탐지 사용 안 함 */
  headerRowIndex?: number;
  /** 시트명 고정 (미지정 시 자동 선택) */
  sheetName?: string;
  /** 헤더 정규화 함수(미지정 시 기본 normalizer 사용) */
  headerNormalizer?: (s: string) => string;
  /** 헤더 자동탐지 스캔 행수 (기본 50) */
  autoDetectScanRows?: number;
  /** 헤더 누락 시 즉시 실패할지 (기본 false: 경고만) */
  failOnMissingHeaders?: boolean;
  /** 경고 중단 정책 (기본 'critical') */
  stopOnWarning?: 'none' | 'critical' | 'all' | WarningCode[];
  /** 너무 큰 파일 방지: 초과분은 잘라냄 + 경고 */
  maxRows?: number;
  /** 경고 콜백 */
  onWarning?: (msg: string, code?: WarningCode) => void;
  /** 에러 콜백 */
  onError?: (err: Error, code?: ExcelWarningCode, subcode?: string) => void;
}

/* =================================
 * Helpers
 * ================================= */

function toError(reason: unknown, fallback = 'Unknown error'): Error {
  if (reason instanceof Error) return reason;
  if (typeof reason === 'string' && reason.trim()) return new Error(reason);
  try {
    return new Error(JSON.stringify(reason));
  } catch {
    return new Error(String(reason ?? fallback));
  }
}

/** Excel(1900 기준) serial → Date */
export function excelSerialToDate(serial: number): Date {
  // Excel epoch is 1899-12-30 (1900 leap bug)
  const base = Date.UTC(1899, 11, 30);
  const ms = serial * 24 * 60 * 60 * 1000;
  return new Date(base + ms);
}

export function formatDateYYYYMMDD(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** 기본 헤더 정규화: 공백/기호 제거 + 소문자 + BOM 제거 */
const defaultHeaderNormalizer = (s: string) =>
  String(s ?? '')
    .replace(/\uFEFF/g, '') // BOM
    .replace(/\s+/g, '') // 모든 공백
    .replace(/[._()\[\]\-]/g, '') // 주요 기호
    .toLowerCase();

/** 경고 정책 판정 */
function shouldStopOnWarning(
  policy: ParseOptions<any>['stopOnWarning'],
  code: WarningCode
): boolean {
  if (policy === 'all') return true;
  if (policy === 'none' || !policy) return false; // parseExcel 내 기본값 'critical'
  if (policy === 'critical') {
    return (
      code === 'MISSING_HEADERS' ||
      code === 'CONVERTER_ERROR' ||
      code === 'SHEET_NOT_FOUND'
    );
  }
  return Array.isArray(policy) && policy.includes(code);
}

/** 경고 발행기: throw 하지 않고 boolean 반환(중단 여부) */
function makeEmitWarn(options: ParseOptions<any>) {
  const policy = options.stopOnWarning ?? 'critical';
  return (msg: string, code: WarningCode): boolean => {
    try {
      options.onWarning?.(msg, code);
    } catch {
      /* no-op */
    }
    // 개발 중에만 필요하면 브라우저 콘솔로도 확인 가능
    // eslint-disable-next-line no-console
    console.warn(`[excel][${code}] ${msg}`);
    return shouldStopOnWarning(policy, code);
  };
}

export interface ConverterTaggedError extends Error {
  code?: string; //  "TYPE:NUMERIC", "TYPE:DATE" ...
  meta?: Record<string, any>;
}

export function makeConvError(
  type: 'NUMERIC' | 'INTEGER' | 'DATE' | 'CODE' | 'BOOLEAN' | string | null,
  message?: string,
  meta?: Record<string, any>
): ConverterTaggedError {
  const e = new Error(message) as ConverterTaggedError;
  e.name = 'ConverterError';
  e.code = `TYPE:${type}`;
  if (meta) e.meta = meta;
  return e;
}

/** =================================
 * Excel → Row[] 파싱
 * 엑셀에 보이는 헤더 문자열을 객체의 필드명으로 매핑
 * 매칭 전에 헤더 문자열을 defaultHeaderNormalizer로 정규화 진행
 * 정규화 규칙(BOM 제거, 모든 공백 제거 . - _ () [] 같은 주요 기호 제거, 영문 소문자로 변경 )
 * normalizedMap[정규화된_엑셀헤더] = Row필드키로 변환
 * 헤더 다음 행부터 본문으로 간주
 * ================================= */

export function parseExcel<Row = Record<string, any>>(
  file: File | Blob,
  options?: ParseOptions<Row>
): Promise<Row[]> {
  if (!options) return Promise.reject(toError('parseOptions is required'));

  const {
    headerMap,
    converters,
    sheetName: preferredSheet,
    headerNormalizer,
    autoDetectScanRows,
    failOnMissingHeaders = false,
    maxRows,
    // onError,
  } = options;

  const emitWarn = makeEmitWarn(options);

  const normalize = headerNormalizer ?? defaultHeaderNormalizer;

  if (
    !headerMap ||
    typeof headerMap !== 'object' ||
    Object.keys(headerMap).length === 0
  ) {
    return Promise.reject(
      toError('parseOptions.headerMap must be a non-empty object')
    );
  }

  const convMap: Partial<Record<StringKeyOf<Row>, Converter>> = (converters ??
    {}) as Partial<Record<StringKeyOf<Row>, Converter>>;

  // 헤더맵을 "정규화된 헤더" → Row 키로 변환
  const normalizedMap: Record<string, StringKeyOf<Row>> = {};
  Object.entries(headerMap).forEach(([excelHeader, fieldKey]) => {
    normalizedMap[normalize(excelHeader)] = fieldKey as StringKeyOf<Row>;
  });
  const normalizedKeys = Object.keys(normalizedMap);

  // 헤더 점수화 (자동탐지용)
  function scoreHeaderRow(row: any[], keys: string[]) {
    const normalizedRow = row.map((h) => normalize(h));
    const set = new Set(normalizedRow);
    let hits = 0;
    for (let i = 0; i < keys.length; i += 1) {
      if (set.has(keys[i])) hits += 1;
    }
    return { hits, normalizedRow };
  }

  function detectHeaderRow(
    table: any[][],
    keys: string[],
    scanRows: number
  ): { index: number; hits: number } {
    let best = { hits: -1, index: 0 };
    const limit = Math.min(scanRows, table.length);
    for (let i = 0; i < limit; i += 1) {
      const { hits } = scoreHeaderRow(table[i], keys);
      if (hits > best.hits) best = { hits, index: i };
    }
    return best;
  }

  // 강건 스캔: 부분일치 허용(너무 느슨하지 않게)
  function approxEqual(a: string, b: string) {
    if (a === b) return true;
    if (a.length >= 3 && (a.includes(b) || b.includes(a))) return true;
    return false;
  }

  function scanHeaders(
    table: any[][],
    keys: string[],
    scanRows: number
  ): {
    headerIndexMap: Map<string, number>;
    headerIdx0: number;
    bestHits: number;
  } {
    const headerIndexMap = new Map<string, number>();
    const headerRowHits: number[] = [];
    const limitR = Math.min(scanRows, table.length);

    for (let r = 0; r < limitR; r += 1) {
      const row = table[r];
      let hits = 0;
      for (let c = 0; c < row.length; c += 1) {
        const cell = normalize(String(row[c] ?? ''));
        if (cell) {
          for (let k = 0; k < keys.length; k += 1) {
            // 매칭 처리...
          }
        }
        for (let k = 0; k < keys.length; k += 1) {
          const key = keys[k];
          if (!headerIndexMap.has(key) && approxEqual(cell, key)) {
            headerIndexMap.set(key, c);
            hits += 1;
          }
        }
      }
      headerRowHits[r] = hits;
    }

    // 히트 최대 행을 헤더 행으로 간주 (최소 2개 이상 매칭일 때만 유효)
    let headerIdx0 = -1;
    let bestHits = 0;
    for (let r = 0; r < headerRowHits.length; r += 1) {
      if (headerRowHits[r] > bestHits) {
        bestHits = headerRowHits[r];
        headerIdx0 = r;
      }
    }
    if (bestHits < 2) headerIdx0 = -1;

    return { headerIndexMap, headerIdx0, bestHits };
  }

  return new Promise<Row[]>((resolve, reject) => {
    const reader = new FileReader();

    const fail = (
      err: unknown,
      errOptions: ParseOptions<any>,
      code?: ExcelWarningCode,
      subcode?: string
      // meta?: Record<string, any>
    ) => {
      const e = toError(err) as Error & { code?: any; subcode?: any };
      if (code) e.code = code;
      if (subcode) e.subcode = subcode;
      try {
        errOptions.onError?.(e, code);
      } catch {
        /* no-op */
      }
      return e;
    };

    reader.onerror = () => {
      reject(
        fail(
          reader.error ?? '파일을 읽는 중 오류가 발생했습니다.',
          options,
          ExcelWarningCode.EMPTY_FILE
        )
      );
    };

    reader.onload = (): void => {
      try {
        if (!reader.result) {
          const msg = '빈 파일이거나 읽을 수 없는 데이터입니다.';
          if (emitWarn(msg, 'EMPTY_FILE')) {
            reject(fail(msg, options, ExcelWarningCode.EMPTY_FILE));
            return;
          }
          resolve([]);
          return;
        }

        const data = new Uint8Array(reader.result as ArrayBuffer);

        let wb: XLSX.WorkBook;
        try {
          wb = XLSX.read(data, { type: 'array', cellDates: true });
        } catch {
          reject(
            fail(
              '이 파일은 엑셀(.xlsx/.xls) 형식이 아니거나 손상되었습니다.',
              options,
              ExcelWarningCode.INVALID_FILE_FORMAT
            )
          );
          return;
        }

        const scanRows =
          typeof autoDetectScanRows === 'number' ? autoDetectScanRows : 50;

        // 1) 시트 선택 (우선순위: 옵션 → 자동탐지 최고 히트 시트)
        let chosenSheet = preferredSheet;
        if (!chosenSheet) {
          const initial = { sheet: wb.SheetNames[0] ?? '', hits: -1 };

          const best = wb.SheetNames.reduce((acc, name) => {
            const ws0 = wb.Sheets[name];
            if (!ws0) return acc;

            const table0 = XLSX.utils.sheet_to_json<any[]>(ws0, {
              header: 1,
              blankrows: false,
              defval: null,
            }) as any[][];

            if (!table0.length) return acc;

            const { hits } = detectHeaderRow(table0, normalizedKeys, scanRows);
            return hits > acc.hits ? { sheet: name, hits } : acc;
          }, initial);

          chosenSheet = best.sheet;
        }

        const ws = chosenSheet ? wb.Sheets[chosenSheet] : undefined;
        if (!ws) {
          const msg = '대상 시트를 찾을 수 없습니다.';
          if (emitWarn(msg, 'SHEET_NOT_FOUND')) {
            reject(fail(msg, options, ExcelWarningCode.SHEET_NOT_FOUND));
            return;
          }
          resolve([]);
          return;
        }

        const table = XLSX.utils.sheet_to_json<any[]>(ws, {
          header: 1,
          blankrows: false,
          defval: null,
        }) as any[][];

        if (!table.length) {
          const msg = '시트가 비어 있습니다.';
          if (emitWarn(msg, 'EMPTY_SHEET')) {
            reject(fail(msg, options, ExcelWarningCode.EMPTY_SHEET));
            return;
          }
          resolve([]);
          return;
        }

        // 2) 헤더 행 결정: 명시적 index > 자동탐지 > 강건스캔 fallback
        let headerIdx0: number;
        if (typeof options.headerRowIndex === 'number') {
          headerIdx0 = Math.max(0, options.headerRowIndex - 1);
          if (headerIdx0 >= table.length) {
            const msg = `headerRowIndex가 시트 범위를 벗어났습니다 (index: ${headerIdx0}, rows: ${table.length}).`;
            reject(fail(msg, options, ExcelWarningCode.TRUNCATED_ROWS));
            return;
          }
        } else {
          const { index } = detectHeaderRow(table, normalizedKeys, scanRows);
          headerIdx0 = index;
        }

        // 3) 1차: 정규화된 헤더 기준으로 매핑
        let headerRow = table[headerIdx0] ?? [];
        let rawHeaderRow = headerRow.map((h) => String(h ?? ''));
        let normalizedHeaderRow = rawHeaderRow.map((h) => normalize(h));

        let headerIndexMap = new Map<string, number>();
        normalizedHeaderRow.forEach((h, idx) => headerIndexMap.set(h, idx));

        let colIndices = normalizedKeys.map((k) => headerIndexMap.get(k) ?? -1);
        let matchedCount = colIndices.filter((i) => i !== -1).length;

        // 4) 1차 매칭 실패 시: 강건 스캔으로 재탐지
        if (matchedCount === 0) {
          const scanned = scanHeaders(table, normalizedKeys, scanRows);
          if (scanned.headerIdx0 >= 0 && scanned.headerIndexMap.size > 0) {
            headerIdx0 = scanned.headerIdx0;
            headerIndexMap = scanned.headerIndexMap;
            headerRow = table[headerIdx0] ?? [];
            rawHeaderRow = headerRow.map((h) => String(h ?? ''));
            normalizedHeaderRow = rawHeaderRow.map((h) => normalize(h));

            colIndices = normalizedKeys.map((k) => headerIndexMap.get(k) ?? -1);
            matchedCount = colIndices.filter((i) => i !== -1).length;
          }
        }

        // 5) 본문 산출 + 과도한 행 컷
        const body = table.slice(headerIdx0 + 1);
        if (maxRows && body.length > maxRows) {
          const msg = `행 수가 많아 ${maxRows}행까지만 파싱합니다. (총 ${body.length}행)`;
          if (emitWarn(msg, 'TRUNCATED_ROWS')) {
            reject(fail(msg, options, ExcelWarningCode.TRUNCATED_ROWS));
            return;
          }
        }
        const limitedBody = maxRows ? body.slice(0, maxRows) : body;

        // 6) 헤더 누락 처리 (정책에 따라 실패/경고)
        const fieldKeys = normalizedKeys.map((k) => normalizedMap[k]);
        const missing = normalizedKeys.filter((_, i) => colIndices[i] === -1);
        if (missing.length) {
          const msg = `헤더를 찾지 못했습니다:`;
          if (failOnMissingHeaders) {
            reject(fail(msg, options, ExcelWarningCode.MISSING_HEADERS));
            return;
          }
          if (emitWarn(msg, 'MISSING_HEADERS')) {
            reject(fail(msg, options, ExcelWarningCode.MISSING_HEADERS));
            return;
          }
        }

        // 7) 본문 → 객체화
        const skipAllEmptyRow = options.skipAllEmptyRow !== false; // 기본 true

        const out: Row[] = [];
        for (let rIdx = 0; rIdx < limitedBody.length; rIdx += 1) {
          const row = limitedBody[rIdx];
          const obj: any = {};
          let nonEmptyCount = 0;

          for (let i = 0; i < fieldKeys.length; i += 1) {
            const colIdx = colIndices[i];
            const fieldKey = fieldKeys[i];
            const cellVal = colIdx >= 0 ? row[colIdx] : null;

            const conv = convMap[fieldKey];
            if (typeof conv === 'function') {
              try {
                obj[fieldKey] = conv(cellVal);
              } catch (e: any) {
                const subcode: string | undefined =
                  e && typeof e.code === 'string' && e.code.startsWith('TYPE:')
                    ? e.code
                    : undefined;
                // const msg = `컨버터 오류 (row=${headerIdx0 + 1 + rIdx + 1}, field=${String(
                //   fieldKey
                // )}): ${e?.message ?? e}`;
                const msg = `${String(fieldKey)} field`;
                // const msg = e?.message ?? e;
                if (emitWarn(msg, 'CONVERTER_ERROR')) {
                  reject(
                    fail(
                      new Error(msg),
                      options,
                      ExcelWarningCode.CONVERTER_ERROR,
                      subcode
                    )
                  );
                  return;
                }
                obj[fieldKey] = null;
              }
            } else {
              obj[fieldKey] = cellVal;
            }

            const v = obj[fieldKey];
            if (!(v === null || v === undefined || String(v).trim() === '')) {
              nonEmptyCount += 1;
            }
          }

          const isAllEmpty = skipAllEmptyRow && nonEmptyCount === 0;
          if (!isAllEmpty) {
            out.push(obj as Row);
          }
        }

        resolve(out);

        if (out.length === 0) {
          reject(
            fail(
              new Error('no data after header'),
              options,
              ExcelWarningCode.NO_DATA_AFTER_HEADER
            )
          );
        }
      } catch (e) {
        // reject(fail(e));
        reject(fail(e, options, ExcelWarningCode.INVALID_FILE_FORMAT));
      }
    };

    if (!(file instanceof Blob)) {
      reject(toError('Not a Blob/File'));
      return;
    }
    reader.readAsArrayBuffer(file);
  });
}

/* =================================
 * 파일 선택 + 파싱 훅
 * ================================= */

export function useExcelParse<Row>(parseOptions: ParseOptions<Row>) {
  const parsing = ref(false);
  const fileName = ref<string>('');
  const lastRows = ref<Row[] | null>(null);
  const lastError = ref<Error | null>(null);
  const lastErrorCode = ref<ExcelWarningCode | null>(null);
  const warnings = ref<string[]>([]);

  // onWarning/onError를 래핑해 상태 저장
  const mergedOptions: ParseOptions<Row> = {
    ...parseOptions,
    onWarning: (msg, code) => {
      warnings.value.push(code ? `[${code}] ${msg}` : msg);
      parseOptions.onWarning?.(msg, code);
    },
    onError: (err, code) => {
      lastError.value = err;
      lastErrorCode.value = code ?? null;
      parseOptions.onError?.(err, code);
    },
  };

  async function parseFromFile(file: File): Promise<Row[]> {
    fileName.value = file.name;
    parsing.value = true;
    lastError.value = null;
    lastErrorCode.value = null;
    warnings.value = [];
    try {
      const rows = await parseExcel<Row>(file, mergedOptions);
      lastRows.value = rows;
      return rows;
    } catch (e: any) {
      lastError.value = toError(e);
      return [];
    } finally {
      parsing.value = false;
    }
  }

  /** 실패를 삼키고 항상 배열을 반환하는 안전 버전 */
  async function parseFromFileSafe(file: File): Promise<Row[]> {
    const rows = await parseFromFile(file);
    return Array.isArray(rows) ? rows : [];
  }

  return {
    parsing,
    fileName,
    lastRows,
    lastError,
    warnings,
    parseFromFile,
    parseFromFileSafe,
  };
}
