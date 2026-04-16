import { TableColumn } from '@/types/dataTable';
import { MockSchema } from '@/types/mock';

export interface ColumnOptions {
  header?: string;
  width?: string;
  align?: string;
  // sortable?: boolean;
  // filterable?: boolean;
  columnClass?: string;
  rowClass?: string;
  visible?: boolean;
  frozen?: boolean;
  id?: string;
}

export type ColumnOptionMap = Record<string, ColumnOptions>;

export function generateMockTableData(
  schema: MockSchema,
  options: ColumnOptionMap = {},
  count: number = 10
): { columns: TableColumn[]; rows: Record<string, any>[] } {
  // 컬럼 생성
  const sampleRowFn = schema.rows[0];
  const sampleRow = Object.fromEntries(
    Object.entries(sampleRowFn).map(([key, fn]) => [key, fn(0)])
  );

  const columns: TableColumn[] = Object.keys(sampleRow).map((field) => {
    const opt = options[field] ?? {};
    return {
      objectId: `grdGuide.${field}`,
      field,
      header: opt.header ?? field,
      width: opt.width ?? '150px',
      columnClass: opt.columnClass ?? 'center',
      rowClass: opt.rowClass ?? 'center',
      visible: opt.visible ?? true,
      frozen: opt.frozen ?? false,
    };
  });

  // row 생성
  const rows: Record<string, any>[] = Array.from({ length: count }, (_, i) => {
    const row = Object.fromEntries(
      Object.entries(sampleRowFn).map(([key, fn]) => [key, fn(i)])
    );
    return {
      id: `rowId${i + 1}`,
      ...row,
    };
  });

  return { columns, rows };
}

// mock.ts
type ValueGen<T = any> = T | ((i: number, rng: Rng) => T);

export interface MakeMockOptions {
  /** 시드 고정(= 같은 결과 재현) */
  seed?: number;
  /** 시작 인덱스(기본 0) */
  startIndex?: number;
  /** 점/브래킷 표기 경로 허용 여부 (기본 true) */
  allowPath?: boolean;
}

export interface Rng {
  next(): number; // [0,1)
  int(min: number, max: number): number; // min~max 포함
  pick<T>(arr: T[]): T;
}

export function makeRng(seed = 1): Rng {
  // m이 2_147_483_647(2^31-1)이어서 JS 정수 정밀도 내에 안전
  const m = 2147483647;
  const a = 16807;

  let s = Math.floor(Math.abs(seed)) % m;
  if (s === 0) s = 1;

  return {
    next() {
      // 비트연산 없이 선형 합동
      s = (s * a) % m;
      // (0,1) 구간의 균일 분포
      return (s - 1) / (m - 1);
    },
    int(min, max) {
      const r = this.next();
      return Math.floor(r * (max - min + 1)) + min;
    },
    pick<T>(arr: T[]) {
      return arr[this.int(0, arr.length - 1)];
    },
  };
}

/** 객체에 경로로 값 설정 (a.b[0].c 지원) */
function setByPath(obj: any, path: string, value: any) {
  const tokens = path
    .replace(/\[(\w+)\]/g, '.$1') // [foo] -> .foo
    .replace(/\[(\d+)\]/g, '.$1') // [0]   -> .0
    .split('.')
    .filter(Boolean);

  let cur = obj;
  for (let i = 0; i < tokens.length; i += 1) {
    const k = tokens[i];
    if (i === tokens.length - 1) {
      cur[k] = value;
      return;
    }
    if (cur[k] == null || typeof cur[k] !== 'object') {
      // 다음 토큰이 숫자면 배열, 아니면 객체
      const next = tokens[i + 1];
      cur[k] = /^\d+$/.test(next) ? [] : {};
    }
    cur = cur[k];
  }
}

/** 통화 포맷(천단위 콤마) */
export const currency = (locale: string, code: string) => (n: number) =>
  new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: code,
    maximumFractionDigits: 0,
  }).format(n);

/** 자주 쓰는 포맷 */
export const krw = currency('ko-KR', 'KRW');
export const usd = currency('en-US', 'USD');
export const eur = currency('de-DE', 'EUR');

/**
 * 키 배열 기반 목업 생성 (기본 규칙 + 선택적 per-key 제너레이터)
 * @param keys 예: ['id','name','price','user.email','items[0].qty']
 * @param count 생성할 행 수
 * @param generators 특정 키에 대한 제너레이터 덮어쓰기
 * @param options 시드/시작 인덱스 등
 */

type Row = Record<string, any>;
// type ValueGen<T = any> = T | ((i: number, rng: Rng) => T);

export function makeMockRows(
  keys: string[],
  count: number,
  generators: Partial<Record<string, ValueGen>> = {},
  options: MakeMockOptions = {}
): Array<Record<string, any>> {
  const { seed = 1, startIndex = 0, allowPath = true } = options;
  const rng = makeRng(seed);
  // const rows: Array<Record<string, any>> = [];

  // 키별 기본 규칙(필요 시 여기서 확장)
  const defaultGen = (key: string): ValueGen => {
    // 숫자 시퀀스 후보
    if (/(id|no|seq|index)$/i.test(key)) {
      return (i: number) => startIndex + i + 1; // 1부터
    }
    // 금액 후보
    if (/amt|amount|price|cost/i.test(key)) {
      return (_i: number, r: Rng) =>
        Math.round(r.int(10_000, 1_000_000) / 100) * 100;
    }
    // 코드류
    if (/code|cd$/i.test(key)) {
      return (i: number) =>
        `${key.toUpperCase()}-${String(startIndex + i + 1).padStart(3, '0')}`;
    }
    // boolean-ish
    if (/^(is|has)[A-Z_]/.test(key)) {
      return (_i: number, r: Rng) => r.next() > 0.5;
    }
    // 기본: 문자열
    return (i: number) => `${key}-${startIndex + i + 1}`;
  };

  const buildRow = (i: number): Row => {
    const row: Row = {};

    keys.forEach((key) => {
      const gen = generators[key] ?? defaultGen(key);
      const val = typeof gen === 'function' ? (gen as any)(i, rng) : gen;

      if (allowPath && /[.[\]]/.test(key)) {
        setByPath(row, key, val);
      } else {
        row[key] = val;
      }
    });

    return row;
  };

  return Array.from({ length: count }, (_, i) => buildRow(i));
}
