import { MockSchema } from '@/types/mock';

const testSchema: MockSchema = {
  columnHeaders: {
    sc: '구분',
    poNo: 'PO 번호',
    partNm: '부품명',
    partNo: '부품번호',
    unit: '단위',
    qty: '수량',
    pric: '가격',
    prgStat: '상태',
    reqDt: '주문날짜',
    dlvReqDt: '납품요청일',
    dlvDueDt: '납품예정일',
    dlvDcdDt: '납품확정일',
    dlvDt: '출고일자',
    shdDt: '선적일자',
    cstmDlvDt: '고객인도일자',
    cretDt: '생성일',
    mdfcDt: '수정일',
  },
  rows: [
    {
      reqCtgrCd: (i) => (Math.floor(i / 2) % 2 === 0 ? 'MRO' : 'Warehouse'),
      poNo: () => {
        const randomStr = Math.random()
          .toString(36)
          .substring(2, 6)
          .toUpperCase();
        const randomNum = Math.floor(Math.random() * 900 + 100);
        return `PO${randomStr}${randomNum}`;
      },
      partNm: (i) => `부품${String.fromCharCode(65 + (i % 26))}`,
      partNo: () => {
        const randomStr = Math.random()
          .toString(36)
          .substring(2, 6)
          .toUpperCase();
        const randomNum = Math.floor(Math.random() * 900 + 100);
        return `PART${randomStr}${randomNum}`;
      },
      unit: () => 'EA',
      qty: (i) => 10 + i,
      pric: (i) => (100 + i * 10).toFixed(2),
      prgStat: (i) => (Math.floor(i / 2) % 2 === 0 ? 'Order' : 'NonOrder'),
      reqDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`,
      dlvReqDt: (i) => `2024-01-${(i + 5).toString().padStart(2, '0')}`,
      dlvDueDt: (i) => `2024-01-${(i + 10).toString().padStart(2, '0')}`,
      dlvDcdDt: (i) => `2024-01-${(i + 7).toString().padStart(2, '0')}`,
      dlvDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`,
      shdDt: (i) => `2024-01-${(i + 5).toString().padStart(2, '0')}`,
      cstmDlvDt: (i) => `2024-01-${(i + 5).toString().padStart(2, '0')}`,
      // cretDt: (i) => `2024-01-${(i + 3).toString().padStart(2, '0')}`,
      // mdfcDt: (i) => `2024-01-${(i + 7).toString().padStart(2, '0')}`,
    },
  ],
};

const SPOV0002Schema: MockSchema = {
  columnHeaders: {
    reqCtgrCd: 'Part', // 구분
    cstmContNo: 'PO No.', // PO 번호
    partNm: 'Description', // 부품명
    partNo: 'Part No', // 부품번호
    unit: 'Unit', // 단위
    qty: 'Quantity', // 수량
    amt: 'Price (EUR)', // 가격
    prgStat: 'Status', // 진행상태
    reqDt: 'Order Date', // 주문 날짜
    dlvReqDt: 'Expected Delivery Date', // 납품요청일
    dlvDueDt: 'Requested Delivery Date', // 납품예정일
    dlvDcdDt: 'Approved Date', // 납품확정일
    fstCretDtm: 'Creation Date', // 생성일
    lastMdfrDtm: 'Modify Date', // 수정일
    // partSeqNo: 'Part No', // 부품순번
  },
  rows: [
    {
      reqCtgrCd: (i) => (Math.floor(i / 2) % 2 === 0 ? 'MRO' : 'Warehouse'), // 구분
      cstmContNo: (i) => 10000 + i * 10, // PO 번호
      partNm: () => 'PIPE,IN TAKE(GROUP)', // 부품명
      partNo: (i) => 100 + i * 10, // 부품번호
      unit: () => 'EA', // 단위
      qty: (i) => (10 + i * 10).toFixed(2), // 수량
      amt: (i) => (100 + i * 10).toFixed(2), // 가격
      // prgStat: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}${['a', 'b', 'b', 'd', 'e'][i % 5]}`, // 진행상태
      prgStat: (i) =>
        ['Order', 'Received', 'Outbound', 'Shipping/Delivered', 'e'][i % 4], // 진행상태
      reqDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 주문 날짜
      dlvReqDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 납품요청일
      dlvDueDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 납품예정일
      dlvDcdDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 납품확정일
      fstCretDtm: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 생성일
      lastMdfrDtm: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 수정일
    },
  ],
};

const SPOV0002P01Schema: MockSchema = {
  columnHeaders: {
    partSeqNo: 'No', // 부품순번
    partNm: 'Description', // 부품명
    partNo: 'Part No', // 부품번호
    unit: 'Unit', // 단위
    lt: 'Lead Time(Day)', // 리드타임
    amtDlr: 'Unit Price (USD)', // 가격
  },
  rows: [
    {
      partSeqNo: (i: number) => 60 - i, // 부품 순번
      partNm: () => 'PIPE,IN TAKE(GROUP)', // 부품명
      partNo: (i) => `PART${12563 + i * 100}`, // 부품번호
      unit: () => 'EA', // 단위
      lt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 리드타임
      amtDlr: (i) => (100 + i * 10).toFixed(2), // 가격
    },
  ],
};

const SPST0001Schema: MockSchema = {
  columnHeaders: {
    reqCtgrCd: 'Part', // 구분
    cstmContNo: 'PO No.', // PO 번호
    partNm: 'Description', // 부품명
    partNo: 'Part No', // 부품번호
    unit: 'Unit', // 단위
    qty: 'Quantity', // 수량
    amt: 'Price (EUR)', // 가격
    prgStat: 'Status', // 진행상태
    reqDt: 'Order Date', // 주문 날짜
    dlvReqDt: 'Expected Delivery Date', // 납품요청일
    dlvDueDt: 'Requested Delivery Date', // 납품예정일
    dlvDcdDt: 'Approved Date', // 납품확정일
    fstCretDtm: 'Creation Date', // 생성일
    lastMdfrDtm: 'Modify Date', // 수정일
    partSeqNo: 'Part No', // 부품순번
  },
  rows: [
    {
      partSeqNo: (i: number) => 60 - i,
      cstmContNo: (i) => 100 + i * 10, // PO 번호
      partNm: () => 'PIPE,IN TAKE(GROUP)', // 부품명
      partNo: (i) => `PART${12563 + i * 100}`, // 부품번호
      unit: () => 'EA', // 단위
      reqDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 주문 날짜
      sttsStndDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 매출날짜
      // rylty: (i) => (10 + i * 10).toFixed(2), // 기술료(원화)
      slsAmtDlr: (i: number) =>
        `$${(2010 + i * 10).toLocaleString('en-US', { minimumFractionDigits: 2 })}`, // 매출금액(USD),
      slsAmtEuro: (i: number) =>
        `€${(213 + i * 10).toLocaleString('en-US', { minimumFractionDigits: 2 })}`, // 매출금액(EUR)
      slsAmt: (i: number) =>
        `\₩${(10000 + i * 10).toLocaleString('en-US', { minimumFractionDigits: 2 })}`, // 매출금액(원화),
    },
  ],
};

const SPOD0002Schema: MockSchema = {
  columnHeaders: {
    partNm: 'Description', // 부품명
    partNo: 'Part No', // 부품번호
    partSeqNo: 'Part No', // 부품순번
    unit: 'Unit', // 단위
    amt: 'Price (USD)', // 가격
    dlvReqDt: 'Expected Delivery Date', // 납품요청일
    dlvDueDt: 'Requested Delivery Date', // 납품예정일
    dlvDcdDt: 'Approved Date', // 납품확정일
    fstCretDtm: 'Creation Date', // 생성일
    lastMdfrDtm: 'Modify Date', // 수정일
  },
  rows: [
    {
      partSeqNo: (i: number) => 60 - i,
      partNm: () => 'PIPE,IN TAKE(GROUP)', // 부품명
      partNo: (i) => `PART${12563 + i * 100}`, // 부품번호
      unit: () => 'EA', // 단위
      lt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 리드타임
      qty: (i) => i * 0,
      amt: (i: number) =>
        `$${(2010 + i * 10).toLocaleString('en-US', { minimumFractionDigits: 2 })}`, // 가격
      dlvReqDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 납품요청일
      dlvDueDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 납품예정일
      dlvDcdDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 납품확정일
    },
  ],
};

const SPCF010SelectRequestListDetailSchema: MockSchema = {
  columnHeaders: {
    // partSeqNo: ''; // 부품순번
    partNm: 'Description', // 부품명
    partNo: 'Part No', // 부품번호
    unit: 'Unit', // 단위
    qty: 'Quantity', // 수량
    lt: 'Lead Time(Day)', // 리드타임
    amt: 'Price (USD)', // 가격
    dlvReqDt: 'Requested Delivery Date', // 납품요청일
    // dlvDueDt: '', // 납품예정일
    // dlvDcdDt: '', // 납품확정일
    // fstCretDtm: '', // 생성일
    // lastMdfrDtm: '', // 수정일
  },
  rows: [
    {
      partSeqNo: (i: number) => 60 - i,
      partNm: () => 'PIPE,IN TAKE(GROUP)', // 부품명
      partNo: (i) => `PART${12563 + i * 100}`, // 부품번호
      unit: () => 'EA', // 단위
      qty: (i) => i * 0, // 수량
      lt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 리드타임
      amt: (i: number) =>
        `$${(2010 + i * 10).toLocaleString('en-US', { minimumFractionDigits: 2 })}`, // 가격
      dlvReqDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 납품요청일
      dlvDueDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 납품예정일
      dlvDcdDt: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 납품확정일
      fstCretDtm: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 생성일
      lastMdfrDtm: (i) => `2024-01-${(i + 1).toString().padStart(2, '0')}`, // 수정일
    },
  ],
};

export {
  SPCF010SelectRequestListDetailSchema,
  SPOD0002Schema,
  SPOV0002P01Schema,
  SPOV0002Schema,
  SPST0001Schema,
  testSchema,
};
