import { http, HttpResponse } from 'msw';

const buildRows = (count: number) =>
  Array.from({ length: count }, (_, i) => ({
    ROW_NO: i + 1,
    ITEM_NO: `ITEM-${String(i + 1).padStart(4, '0')}`,
    ITEM_NM: `샘플 항목 ${i + 1}`,
    STATUS: ['A', 'B', 'C'][i % 3],
    STATUS_NM: ['활성', '대기', '종료'][i % 3],
    REG_DT: `2024${String((i % 12) + 1).padStart(2, '0')}${String((i % 28) + 1).padStart(2, '0')}`,
    REG_NM: `등록자 ${i + 1}`,
    REMARK: `비고 내용 ${i + 1}`,
    AMT: (i + 1) * 10000,
  }));

const mockRows = buildRows(30);

const treeNodes = [
  {
    NODE_ID: '100',
    PARENT_ID: null,
    NODE_NM: '전체',
    LEVEL: 1,
    LEAF_YN: 'N',
  },
  {
    NODE_ID: '110',
    PARENT_ID: '100',
    NODE_NM: '카테고리 A',
    LEVEL: 2,
    LEAF_YN: 'N',
  },
  {
    NODE_ID: '111',
    PARENT_ID: '110',
    NODE_NM: '항목 A-1',
    LEVEL: 3,
    LEAF_YN: 'Y',
  },
  {
    NODE_ID: '112',
    PARENT_ID: '110',
    NODE_NM: '항목 A-2',
    LEVEL: 3,
    LEAF_YN: 'Y',
  },
  {
    NODE_ID: '120',
    PARENT_ID: '100',
    NODE_NM: '카테고리 B',
    LEVEL: 2,
    LEAF_YN: 'N',
  },
  {
    NODE_ID: '121',
    PARENT_ID: '120',
    NODE_NM: '항목 B-1',
    LEVEL: 3,
    LEAF_YN: 'Y',
  },
  {
    NODE_ID: '122',
    PARENT_ID: '120',
    NODE_NM: '항목 B-2',
    LEVEL: 3,
    LEAF_YN: 'Y',
  },
];

export const templateHandlers = [
  // Type A / C — 일반 목록 조회
  http.post('/online/mvcJson/SCREEN_ID-selectList', async () => {
    return HttpResponse.json({ payload: { dsOutput: mockRows } });
  }),

  // Type C — 트리 목록 조회
  http.post('/online/mvcJson/SCREEN_ID-selectTreeList', async () => {
    return HttpResponse.json({ payload: { dsOutput: treeNodes } });
  }),

  // Type B — 단건 상세 조회
  http.post('/online/mvcJson/SCREEN_ID-selectDetail', async () => {
    return HttpResponse.json({ payload: { dsOutput: [mockRows[0]] } });
  }),

  // Type B — 저장 (등록/수정)
  http.post('/online/mvcJson/SCREEN_ID-insert', async () => {
    return HttpResponse.json({ payload: { result: 'SUCCESS' } });
  }),
  http.post('/online/mvcJson/SCREEN_ID-update', async () => {
    return HttpResponse.json({ payload: { result: 'SUCCESS' } });
  }),
  http.post('/online/mvcJson/SCREEN_ID-delete', async () => {
    return HttpResponse.json({ payload: { result: 'SUCCESS' } });
  }),

  // Type D — 마스터 목록
  http.post('/online/mvcJson/SCREEN_ID-selectMasterList', async () => {
    return HttpResponse.json({ payload: { dsOutput: buildRows(5) } });
  }),

  // Type D — 상세 목록
  http.post('/online/mvcJson/SCREEN_ID-selectDetailList', async () => {
    return HttpResponse.json({ payload: { dsOutput: mockRows } });
  }),
];
