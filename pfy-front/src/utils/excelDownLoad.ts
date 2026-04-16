import * as XLSX from 'xlsx';

import { Column } from '@/components/common/dataTable2/types';

const getDateTimeString = () => {
  const d = new Date();

  const pad = (n: number) => n.toString().padStart(2, '0');

  return (
    d.getFullYear().toString() +
    pad(d.getMonth() + 1) +
    pad(d.getDate()) +
    pad(d.getHours()) +
    pad(d.getMinutes()) +
    pad(d.getSeconds())
  );
};

// visualWidth 함수
const visualWidth = (value: unknown) => {
  const text = value == null ? '' : String(value);

  const lines = text.split(/\r?\n/);

  const widthOf = (s: string) => {
    return Array.from(s).reduce((w, ch) => {
      const code = ch.codePointAt(0) || 0;

      // East Asian Width 속성에 따른 전각 문자 판별 (2폭)

      if (
        // CJK 통합 한자 (중국어, 일본어, 한국어 한자)
        (code >= 0x4e00 && code <= 0x9fff) ||
        (code >= 0x3400 && code <= 0x4dbf) ||
        (code >= 0x20000 && code <= 0x2a6df) || // 한글
        (code >= 0xac00 && code <= 0xd7af) || // 한글 음절
        (code >= 0x1100 && code <= 0x11ff) || // 한글 자모
        (code >= 0x3130 && code <= 0x318f) || // 한글 호환 자모
        // 일본어 히라가나, 가타카나
        (code >= 0x3040 && code <= 0x309f) ||
        (code >= 0x30a0 && code <= 0x30ff) ||
        // 전각 ASCII 및 기호

        (code >= 0xff00 && code <= 0xffef) ||
        // CJK 기호 및 구두점

        (code >= 0x3000 && code <= 0x303f) ||
        // 기타 동아시아 기호들

        (code >= 0x2e80 && code <= 0x2eff) ||
        // CJK 라디칼 보충

        (code >= 0x31c0 && code <= 0x31ef) ||
        // CJK 획

        (code >= 0xf900 && code <= 0xfaff) ||
        // CJK 호환 한자

        // 이모지 (대부분 2폭으로 표시됨)

        (code >= 0x1f000 && code <= 0x1f9ff) ||
        (code >= 0x2600 && code <= 0x26ff) ||
        (code >= 0x2700 && code <= 0x27bf) ||
        (code >= 0x1f300 && code <= 0x1f5ff) ||
        (code >= 0x1f600 && code <= 0x1f64f) ||
        (code >= 0x1f680 && code <= 0x1f6ff) ||
        (code >= 0x1f900 && code <= 0x1f9ff) ||
        // 기타 넓은 문자들

        (code >= 0x2329 && code <= 0x232a) // 괄호
      ) {
        return w + 2;
      }

      // 제어 문자, 결합 문자 등 (0폭)

      if (
        (code >= 0x0000 && code <= 0x001f) ||
        // C0 제어 문자

        (code >= 0x007f && code <= 0x009f) ||
        // C1 제어 문자

        (code >= 0x0300 && code <= 0x036f) ||
        // 결합 분음 부호

        (code >= 0x1ab0 && code <= 0x1aff) ||
        // 결합 분음 부호 확장

        (code >= 0x1dc0 && code <= 0x1dff) ||
        // 결합 분음 부호 보충

        (code >= 0x20d0 && code <= 0x20ff) ||
        // 결합 기호

        (code >= 0xfe20 && code <= 0xfe2f) // 결합 반각 기호
      ) {
        return w;
        // 폭 추가하지 않음
      }

      // 나머지는 모두 반각 (1폭) - 라틴어, 키릴문자, 아랍어, 히브리어, 인도계 문자 등

      return w + 1;
    }, 0);
  };

  return Math.max(0, ...lines.map(widthOf));
};

const makeAutoCols = (
  col: {
    header: string;
    field: string;
  }[],

  d: Record<string, any>[],

  pad = 2,

  min = 8,

  max = 60
) => {
  return col.map((el) => {
    const headerW = visualWidth(el.header);

    const dataW = Math.max(0, ...d.map((row) => visualWidth(row[el.field])));

    const wch = Math.min(Math.max(Math.max(headerW, dataW) + pad, min), max);

    return {
      wch,
    };
  });
};

type Conditions = {
  [key: string]: string;
};

const downloadExcel = ({
  columns,
  data,
  sheets, // 멀티 시트 데이터 추가
  title,
  searchConditions,
}: {
  columns: Column[];
  data?: Record<string, any>[]; // 단일 시트용 (optional로 변경)
  sheets?: Record<string, Record<string, any>[]>; // 멀티 시트용 추가
  title: string;
  searchConditions?: Conditions[];
}) => {
  // rowIndex 필드를 가진 컬럼 제외
  const filteredColumns = columns.filter(
    (column) => column.field !== 'rowIndex'
  );

  const now = getDateTimeString();
  const filename = `${now}_${title}.xlsx`;

  // 워크북 생성
  const wb = XLSX.utils.book_new();

  // sheets가 있으면 멀티 시트로 처리
  if (sheets && Object.keys(sheets).length > 0) {
    Object.entries(sheets).forEach(([sheetName, sheetData]) => {
      // 1행: 메뉴 이름 (필수)
      const firstRow = [`▣ ${title}`];

      // 2행 이후: 커스텀 텍스트 여러 줄 (선택)

      // const secondRows =
      //   searchConditions && searchConditions.length > 0
      //     ? [
      //         [
      //           searchConditions
      //             .map((line) => `${line.label}: ${line.value}`)
      //             .join(' '),
      //         ],
      //       ]
      //     : [];

      // 컬럼 헤더
      const excelHeader = filteredColumns.map((col) => col.header);

      // 데이터 행들
      const excelData = sheetData.map((row) =>
        filteredColumns.map((col) => row[col.field])
      );

      // 전체 배열 합치기
      const wsData = [firstRow, excelHeader, ...excelData];

      // 시트 생성
      const ws = XLSX.utils.aoa_to_sheet(wsData);

      // 컬럼 너비 설정
      const autoCols = makeAutoCols(
        filteredColumns.map((c) => ({
          header: c.header,
          field: c.field,
        })),

        sheetData
      );

      ws['!cols'] = autoCols;

      // 병합 영역 설정

      ws['!merges'] = [];

      ws['!merges'].push({
        s: {
          r: 0,
          c: 0,
        },

        e: {
          r: 0,
          c: filteredColumns.length - 1,
        },
      });

      // for (let i = 0; i < secondRows.length; i += 1) {
      //   ws['!merges'].push({
      //     s: {
      //       r: i + 1,
      //       c: 0,
      //     },

      //     e: {
      //       r: i + 1,
      //       c: columns.length - 1,
      //     },
      //   });
      // }

      // 행 높이 설정

      ws['!rows'] = [];

      ws['!rows'][0] = {
        hpt: 30,
      };

      // for (let i = 0; i < secondRows.length; i += 1) {
      //   ws['!rows'][i + 1] = {
      //     hpt: 25,
      //   };
      // }

      // 워크북에 시트 추가

      XLSX.utils.book_append_sheet(wb, ws, sheetName);
    });
  } else if (data) {
    // 기존 단일 시트 로직 (변경 없음)
    const firstRow = [`▣ ${title}`];

    // const secondRowText = searchConditions
    //   ? searchConditions.map((line) => `${line.label}:${line.value}`).join(' ')
    //   : '';

    // const secondRows = secondRowText ? [[secondRowText]] : [];

    const excelHeader = filteredColumns.map((col) => col.header);

    const excelData = data.map((row) =>
      filteredColumns.map((col) => row[col.field])
    );

    const wsData = [
      firstRow,
      // ...secondRows,
      excelHeader,
      ...excelData,
    ];

    const ws = XLSX.utils.aoa_to_sheet(wsData);

    const autoCols = makeAutoCols(
      filteredColumns.map((c) => ({
        header: c.header,
        field: c.field,
      })),

      data
    );

    ws['!cols'] = autoCols;

    ws['!merges'] = [];

    ws['!merges'].push({
      s: {
        r: 0,
        c: 0,
      },

      e: {
        r: 0,
        c: filteredColumns.length - 1,
      },
    });

    // for (let i = 0; i < secondRows.length; i += 1) {
    //   ws['!merges'].push({
    //     s: {
    //       r: i + 1,
    //       c: 0,
    //     },

    //     e: {
    //       r: i + 1,
    //       c: columns.length - 1,
    //     },
    //   });
    // }

    ws['!rows'] = [];

    ws['!rows'][0] = {
      hpt: 30,
    };

    // for (let i = 0; i < secondRows.length; i += 1) {
    //   ws['!rows'][i + 1] = {
    //     hpt: 25,
    //   };
    // }

    XLSX.utils.book_append_sheet(wb, ws, title);
  }

  XLSX.writeFile(wb, filename);
};

export { downloadExcel };
