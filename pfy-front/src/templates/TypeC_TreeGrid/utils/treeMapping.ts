import type { MainData, TreeNode } from '../types';

/** 백엔드 미기동·빈 payload 시 우측 그리드용 (MSW mockRows 와 동일 필드) */
export function getTypeCDemoListRows(): MainData[] {
  return Array.from({ length: 12 }, (_, i) => ({
    ITEM_NO: `ITEM-${String(i + 1).padStart(4, '0')}`,
    ITEM_NM: `샘플 항목 ${i + 1}`,
    STATUS: ['A', 'B', 'C'][i % 3],
    STATUS_NM: ['활성', '대기', '종료'][i % 3],
    REG_DT: `202401${String((i % 28) + 1).padStart(2, '0')}`,
    REG_USER_NM: `등록자 ${i + 1}`,
  }));
}

function rowId(item: Record<string, any>): string {
  const v =
    item.NODE_KEY ??
    item.NODE_ID ??
    item.MENU_ID ??
    item.deptCd;
  return v != null && v !== '' ? String(v) : '';
}

function parentId(item: Record<string, any>): string | null {
  const v =
    item.PARENT_KEY ??
    item.PARENT_ID ??
    item.pDeptCd;
  if (v == null || v === '') return null;
  return String(v);
}

function rowLabel(item: Record<string, any>, id: string): string {
  return (
    item.NODE_NM ??
    item.MENU_NM ??
    item.deptNm ??
    id
  );
}

function inferLeaf(item: Record<string, any>): boolean {
  if (typeof item.IS_LEAF === 'boolean') return item.IS_LEAF;
  if (item.LEAF_YN === 'Y') return true;
  if (item.LEAF_YN === 'N') return false;
  return false;
}

function mapNestedItem(item: Record<string, any>): TreeNode {
  const key = rowId(item);
  const label = rowLabel(item, key);
  const rawChildren = item.children;
  const children =
    Array.isArray(rawChildren) && rawChildren.length > 0
      ? rawChildren.map((c: Record<string, any>) => mapNestedItem(c))
      : undefined;
  const leaf = !children?.length;

  return {
    key,
    label,
    data: {
      ...item,
      menuNm: label,
      menuId: key,
    },
    icon: leaf ? 'pi pi-file' : 'pi pi-folder',
    children,
    leaf,
  };
}

function mapFlatToTree(data: Record<string, any>[]): TreeNode[] {
  const nodeMap = new Map<string, TreeNode>();
  const validRows = data.filter((item) => rowId(item));

  validRows.forEach((item) => {
    const id = rowId(item);
    const label = rowLabel(item, id);
    const leaf = inferLeaf(item);
    nodeMap.set(id, {
      key: id,
      label,
      data: {
        ...item,
        menuNm: label,
        menuId: id,
      },
      icon: leaf ? 'pi pi-file' : 'pi pi-folder',
      children: [],
      leaf,
    });
  });

  const roots: TreeNode[] = [];

  validRows.forEach((item) => {
    const id = rowId(item);
    const node = nodeMap.get(id);
    if (!node) return;
    const p = parentId(item);
    if (p && nodeMap.has(p)) {
      nodeMap.get(p)!.children!.push(node);
    } else {
      roots.push(node);
    }
  });

  return roots;
}

/** MSW / 백엔드 샘플용 — 화면 미리보기 */
export function getTypeCDemoMenuTree(): TreeNode[] {
  return [
    {
      key: 'ROOT',
      label: 'Menu Tree',
      data: { menuNm: 'Menu Tree', menuId: 'ROOT' },
      icon: 'pi pi-folder',
      leaf: false,
      children: [
        {
          key: 'ROOT01',
          label: 'Dashboard',
          data: { menuNm: 'Dashboard', menuId: 'ROOT01' },
          icon: 'pi pi-folder',
          leaf: false,
          children: [
            {
              key: 'ROOT0101',
              label: 'Dashboard (Admin)',
              data: { menuNm: 'Dashboard (Admin)', menuId: 'ROOT0101' },
              icon: 'pi pi-file',
              leaf: true,
            },
            {
              key: 'ROOT0102',
              label: 'Dashboard (User)',
              data: { menuNm: 'Dashboard (User)', menuId: 'ROOT0102' },
              icon: 'pi pi-file',
              leaf: true,
            },
          ],
        },
        {
          key: 'ROOT02',
          label: 'Master Data Management',
          data: { menuNm: 'Master Data Management', menuId: 'ROOT02' },
          icon: 'pi pi-folder',
          leaf: false,
          children: [
            {
              key: 'ROOT0201',
              label: 'Project',
              data: { menuNm: 'Project', menuId: 'ROOT0201' },
              icon: 'pi pi-file',
              leaf: true,
            },
            {
              key: 'ROOT0202',
              label: 'Contract',
              data: { menuNm: 'Contract', menuId: 'ROOT0202' },
              icon: 'pi pi-file',
              leaf: true,
            },
          ],
        },
      ],
    },
  ];
}

/**
 * API dsOutput → 템플릿 TreeNode[]
 * - sycc040 계열: children 중첩 배열
 * - 평면: NODE_KEY·PARENT_KEY·IS_LEAF 또는 NODE_ID·PARENT_ID·LEAF_YN (MSW 템플릿)
 */
export function mapApiRowsToTreeNodes(data: unknown): TreeNode[] {
  if (!Array.isArray(data) || data.length === 0) return [];

  const rows = data as Record<string, any>[];
  const hasNestedChildren = rows.some(
    (row) => Array.isArray(row.children) && row.children.length > 0
  );

  if (hasNestedChildren) {
    return rows.map((row) => mapNestedItem(row));
  }

  return mapFlatToTree(rows);
}
