import dayjs from 'dayjs';
import { http, HttpResponse } from 'msw';

import { generateMockTableData, makeMockRows } from '@/composables/useMockData';
import {
  SPOD0002Schema,
  SPOV0002P01Schema,
  SPOV0002Schema,
  SPST0001Schema,
  testSchema,
} from '@/mocks/schema/SPSchema';
import { MockSchema } from '@/types/mock';

type ColumnOption = {
  header: string;
  width?: string;
  columnClass?: string;
  rowClass?: string;
  visible?: boolean;
  frozen?: boolean;
};

type ColumnHeaders = Record<string, string>;
type CustomMap = Record<string, string>;

const defaultColumnOption: Omit<ColumnOption, 'header'> = {
  width: '140px',
  columnClass: 'center',
  rowClass: 'center',
  visible: true,
  frozen: false,
};

const createColumnOptions = (
  headers: ColumnHeaders,
  widths: CustomMap = {},
  columnClass: CustomMap = {}
): Record<string, ColumnOption> => {
  return Object.fromEntries(
    Object.entries(headers).map(([field, header]) => [
      field,
      {
        ...defaultColumnOption,
        header,
        width: widths[field] ?? defaultColumnOption.width,
        columnClass: columnClass[field] ?? defaultColumnOption.columnClass,
      },
    ])
  );
};

export const SPhandlers = [
  http.get('/api/sp/list', ({ request }) => {
    const url = new URL(request.url);
    const screenId = url.searchParams.get('screenId');
    const length = url.searchParams.get('length');

    if (!screenId) {
      return HttpResponse.json({ error: 'Missing screenId' }, { status: 400 });
    }

    let schema: MockSchema;

    switch (screenId) {
      case 'testGuide':
        schema = testSchema;
        break;
      case 'spov0002':
        schema = SPOV0002Schema;
        break;
      default:
        return HttpResponse.json({ error: 'Unknown schema' }, { status: 400 });
    }

    const columnOptions = createColumnOptions(schema.columnHeaders);

    const { columns, rows } = generateMockTableData(
      schema,
      columnOptions,
      Number(length)
    );

    return HttpResponse.json({ columns, rows });
  }),

  http.get('/SPST010/selectStatisticsList', ({ request }) => {
    const url = new URL(request.url);
    const screenId = url.searchParams.get('screenId');
    const length = url.searchParams.get('length');

    if (!screenId) {
      return HttpResponse.json({ error: 'Missing screenId' }, { status: 400 });
    }

    let schema: MockSchema;

    switch (screenId) {
      case 'SPST010':
        schema = SPST0001Schema;
        break;
      default:
        return HttpResponse.json({ error: 'Unknown schema' }, { status: 400 });
    }

    const columnOptions = createColumnOptions(schema.columnHeaders);

    const { columns, rows } = generateMockTableData(
      schema,
      columnOptions,
      Number(length)
    );

    return HttpResponse.json({ columns, rows });
  }),

  http.get('/SPOV010P01/prodList', ({ request }) => {
    const url = new URL(request.url);
    const screenId = url.searchParams.get('screenId');
    const length = url.searchParams.get('length');

    if (!screenId) {
      return HttpResponse.json({ error: 'Missing screenId' }, { status: 400 });
    }

    let schema: MockSchema;

    switch (screenId) {
      case 'SPOV010P01':
        schema = SPOV0002P01Schema;
        break;
      default:
        return HttpResponse.json({ error: 'Unknown schema' }, { status: 400 });
    }

    const columnOptions = createColumnOptions(schema.columnHeaders);

    const { columns, rows } = generateMockTableData(
      schema,
      columnOptions,
      Number(length)
    );

    return HttpResponse.json({ columns, rows });
  }),

  http.get('SPOD010/selectRequestCartList', ({ request }) => {
    const url = new URL(request.url);
    const screenId = url.searchParams.get('screenId');
    const length = url.searchParams.get('length');

    if (!screenId) {
      return HttpResponse.json({ error: 'Missing screenId' }, { status: 400 });
    }

    const cartLst = makeMockRows(
      [
        'cstmCd',
        'cartNm',
        'cartNo',
        'totPurQty',
        'qty',
        'amt',
        'fstCretDtm',
        'lastMdfrDtm',
      ],
      Number(length),
      {
        cstmCd: '2',
        cartNm: (i: any) =>
          `PO_${dayjs(new Date()).format('YYYYMMDD')}-00${1 + i}`,
        totPurQty: (i: any) => 1 + i * 1,
        cartNo: (i: any) =>
          `PO-${dayjs(new Date()).format('YYYYMMDD')}-00${1 + i}`,
        qty: (i: any) => 10 + i * 10,
        fstCretDtm: new Date(),
        amt: (i: number) =>
          `$${(2010 + i * 10).toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
        lastMdfrDtm: new Date(),
      }
    );

    return HttpResponse.json({ cartLst });
  }),

  http.get('SPOD010/selectRequestList', async ({ request }) => {
    const url = new URL(request.url);
    const screenId = url.searchParams.get('screenId');
    const length = url.searchParams.get('length');

    if (!screenId) {
      return HttpResponse.json({ error: 'Missing screenId' }, { status: 400 });
    }

    let schema: MockSchema;

    switch (screenId) {
      case 'SPOD010':
        schema = SPOD0002Schema;
        break;
      default:
        return HttpResponse.json({ error: 'Unknown schema' }, { status: 400 });
    }

    const columnOptions = createColumnOptions(schema.columnHeaders);

    const { columns, rows } = generateMockTableData(
      schema,
      columnOptions,
      Number(length)
    );

    return HttpResponse.json({ columns, rows });
  }),

  http.get('/online/mvcJson/SPCF010-selectRequestList', ({ request }) => {
    const url = new URL(request.url);
    const screenId = url.searchParams.get('screenId');
    const length = url.searchParams.get('length');

    if (!screenId) {
      return HttpResponse.json({ error: 'Missing screenId' }, { status: 400 });
    }

    const cartLst = makeMockRows(
      [
        'cstmCd',
        'cartNo',
        'cstmContNo',
        'cartNm',
        'qty',
        'amt',
        'reqDt',
        'fstCretDtm',
        'lastMdfrDtm',
      ],
      Number(length),
      {
        cstmCd: '2',
        cartNo: (i: any) =>
          `SP-${dayjs(new Date()).format('YYYYMMDD')}-00${1 + i}`,
        cstmContNo: (i: any) =>
          `SP-${dayjs(new Date()).format('YYYYMMDD')}-00${1 + i}`,
        cartNm: (i: any) =>
          `CART_${dayjs(new Date()).format('YYYYMMDD')}-00${1 + i}`,
        totPurQty: (i: any) => 1 + i * 1,
        qty: (i: any) => 10 + i * 10,
        amt: (i: number) =>
          `$${(2010 + i * 10).toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
        fstCretDtm: new Date(),
        lastMdfrDtm: new Date(),
      }
    );

    return HttpResponse.json({ cartLst });
  }),

  http.get('/online/mvcJson/SPCF010-selectRequestListDetail', ({ request }) => {
    const url = new URL(request.url);
    const screenId = url.searchParams.get('screenId');
    const length = url.searchParams.get('length');

    if (!screenId) {
      return HttpResponse.json({ error: 'Missing screenId' }, { status: 400 });
    }

    let schema: MockSchema;

    switch (screenId) {
      case 'SPOD010':
        schema = SPOD0002Schema;
        break;
      default:
        return HttpResponse.json({ error: 'Unknown schema' }, { status: 400 });
    }

    const columnOptions = createColumnOptions(schema.columnHeaders);

    const { columns, rows } = generateMockTableData(
      schema,
      columnOptions,
      Number(length)
    );

    return HttpResponse.json({ columns, cartDtlLst: rows });
  }),
];
