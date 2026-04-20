import type { FieldDef, FieldType } from '../types';

/** 날짜 문자열을 인덱스 기반으로 생성 (2024년, 순환) */
function mockDate(i: number): string {
  const month = String((i % 12) + 1).padStart(2, '0');
  const day   = String((i % 28) + 1).padStart(2, '0');
  return `2024-${month}-${day}`;
}

/** 한국어 더미 텍스트 (label 기반) */
function mockText(label: string, i: number): string {
  return `${label} ${i + 1}번 항목`;
}

/** TypeScript 인터페이스 필드 타입 문자열 반환 */
function tsType(fieldType: FieldType): string {
  switch (fieldType) {
    case 'number':    return 'number';
    case 'checkbox':  return 'boolean';
    default:          return 'string';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Public API
// ─────────────────────────────────────────────────────────────────────────────

export interface MockGenResult {
  /** TypeScript interface 선언 문자열 */
  interfaceCode: string;
  /** MOCK_DATA 상수 선언 문자열 */
  mockDataCode: string;
  /** searchParams 초기값 객체 리터럴 문자열 */
  searchParamsCode: string;
  /** select/radio/badge 필드별 options 상수 선언들 */
  optionsCode: string;
}

/**
 * 필드 정의로부터 TypeScript 인터페이스, mock 데이터, searchParams 를 생성.
 * @param fields   전체 필드 정의
 * @param rowCount 생성할 mock row 수 (기본 20)
 */
export function generateMockAssets(fields: FieldDef[], rowCount = 20): MockGenResult {
  const allFields  = fields;
  const dataFields = fields.filter(f => f.listable || f.detailable);

  // ── 1. TypeScript interface ───────────────────────────────────────────────
  const interfaceLines: string[] = ['  id: number;'];
  for (const f of dataFields) {
    interfaceLines.push(`  ${f.key}: ${tsType(f.type)};`);
    if (f.type === 'select' || f.type === 'radio' || f.type === 'badge') {
      interfaceLines.push(`  ${f.key}Nm: string;`);
    }
    if (f.type === 'badge') {
      interfaceLines.push(`  ${f.key}Color: string;`);
    }
  }
  const interfaceCode = `interface RowItem {\n${interfaceLines.join('\n')}\n}`;

  // ── 2. MOCK_DATA rows ─────────────────────────────────────────────────────
  const rows: string[] = [];
  for (let i = 0; i < rowCount; i++) {
    const props: string[] = [`id: ${i + 1}`];

    for (const f of dataFields) {
      switch (f.type) {
        case 'text':
        case 'textarea':
          props.push(`${f.key}: '${mockText(f.label, i)}'`);
          break;

        case 'number':
          props.push(`${f.key}: ${(i + 1) * 1000}`);
          break;

        case 'date':
        case 'daterange':
          props.push(`${f.key}: '${mockDate(i)}'`);
          break;

        case 'select':
        case 'radio':
        case 'badge': {
          const opts = f.options ?? [];
          const opt  = opts.length ? opts[i % opts.length] : null;
          props.push(`${f.key}: '${opt?.value ?? ''}'`);
          props.push(`${f.key}Nm: '${opt?.label ?? ''}'`);
          if (f.type === 'badge') {
            props.push(`${f.key}Color: '${opt?.color ?? 'blue'}'`);
          }
          break;
        }

        case 'checkbox':
          props.push(`${f.key}: ${i % 2 === 0}`);
          break;
      }
    }

    rows.push(`  { ${props.join(', ')} }`);
  }
  const mockDataCode = `const MOCK_DATA: RowItem[] = [\n${rows.join(',\n')},\n];`;

  // ── 3. searchParams 초기값 ────────────────────────────────────────────────
  const searchFields = allFields.filter(f => f.searchable);
  const searchProps: string[] = [];
  for (const f of searchFields) {
    if (f.type === 'daterange') {
      searchProps.push(`  ${f.key}From: ''`);
      searchProps.push(`  ${f.key}To: ''`);
    } else if (f.type === 'number') {
      searchProps.push(`  ${f.key}: undefined as number | undefined`);
    } else {
      searchProps.push(`  ${f.key}: ''`);
    }
  }
  const searchParamsCode = searchProps.length
    ? `const searchParams = reactive({\n${searchProps.join(',\n')},\n});`
    : `const searchParams = reactive({});`;

  // ── 4. options 상수 (select / radio / badge 필드) ─────────────────────────
  const optionFields = allFields.filter(
    f => (f.type === 'select' || f.type === 'radio' || f.type === 'badge') && f.options?.length
  );
  const optionLines: string[] = [];
  for (const f of optionFields) {
    const items = (f.options ?? [])
      .map(o => `  { label: '${o.label}', value: '${o.value}'${o.color ? `, color: '${o.color}'` : ''} }`)
      .join(',\n');
    optionLines.push(`const ${f.key}Options = [\n  { label: '전체', value: '' },\n${items},\n];`);
  }
  const optionsCode = optionLines.join('\n\n');

  return { interfaceCode, mockDataCode, searchParamsCode, optionsCode };
}

/**
 * 검색 필드를 기반으로 computed filteredRows 함수 본문을 생성.
 * 클라이언트 사이드 필터 — API 연동 없이 mock 데이터를 필터링.
 */
export function generateFilterLogic(fields: FieldDef[]): string {
  const searchFields = fields.filter(f => f.searchable);
  const checks: string[] = [];

  for (const f of searchFields) {
    if (f.type === 'daterange') {
      checks.push(
        `  if (searchParams.${f.key}From) rows = rows.filter(r => r.${f.key} >= searchParams.${f.key}From);`,
        `  if (searchParams.${f.key}To)   rows = rows.filter(r => r.${f.key} <= searchParams.${f.key}To);`,
      );
    } else if (f.type === 'text' || f.type === 'textarea') {
      checks.push(
        `  if (searchParams.${f.key}) rows = rows.filter(r => r.${f.key}.includes(searchParams.${f.key}));`,
      );
    } else if (f.type === 'number') {
      checks.push(
        `  if (searchParams.${f.key} != null) rows = rows.filter(r => r.${f.key} === searchParams.${f.key});`,
      );
    } else {
      // select, radio, badge
      checks.push(
        `  if (searchParams.${f.key}) rows = rows.filter(r => r.${f.key} === searchParams.${f.key});`,
      );
    }
  }

  if (checks.length === 0) return '  return rows;';
  return `  let rows = allRows.value;\n${checks.join('\n')}\n  return rows;`;
}
