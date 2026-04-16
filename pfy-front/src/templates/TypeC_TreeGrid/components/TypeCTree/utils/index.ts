import type { TreeNode as PrimeTreeNode } from 'primevue/treenode';

import type { TreeTableColumn } from '@/components/common/treeTable/types';
import type { TreeNode } from '../../../types';

/** sycc040 `getDeptTreeColumns` 패턴 — 메뉴명(익스팬더) + 메뉴 ID */
export function getMenuTreeColumns(): TreeTableColumn[] {
  return [
    {
      objectId: 'tree.menuNm',
      field: 'menuNm',
      header: '메뉴명',
      width: 'auto',
      columnClass: 'center',
      rowClass: 'left',
      visible: true,
      frozen: false,
      expander: true,
    },
    {
      objectId: 'tree.menuId',
      field: 'menuId',
      header: '메뉴 ID',
      width: '120px',
      columnClass: 'center',
      rowClass: 'center',
      visible: true,
    },
  ];
}

export function convertToTreeTableNodes(nodes: TreeNode[]): PrimeTreeNode[] {
  const convert = (node: TreeNode): PrimeTreeNode => ({
    key: node.key,
    data: {
      menuNm: node.data?.menuNm ?? node.label,
      menuId: node.data?.menuId ?? node.key,
      nodeName: node.label,
      nodeKey: node.key,
      icon: node.icon ?? '',
      isLeaf: node.leaf ?? !node.children?.length,
      ...(node.data ?? {}),
    },
    children: node.children?.length
      ? node.children.map(convert)
      : undefined,
  });

  return annotateLevels(nodes.map(convert));
}

/** sycc040 `annotateLevels` — 트리 연결선(tt-level-*) SCSS와 연동 */
export function annotateLevels(
  nodes: PrimeTreeNode[],
  level = 1
): PrimeTreeNode[] {
  if (!nodes?.length) return [];

  return nodes.map((n, idx) => {
    const children = n.children
      ? annotateLevels(n.children, level + 1)
      : undefined;

    return {
      ...n,
      data: {
        ...(n.data ?? {}),
        level,
        isFirstOfLevel: idx === 0,
        isLastOfLevel: idx === nodes.length - 1,
      },
      styleClass: [
        `tt-level-${level}`,
        idx === 0 ? 'tt-first-of-level' : '',
        idx === nodes.length - 1 ? 'tt-last-of-level' : '',
      ]
        .filter(Boolean)
        .join(' '),
      children,
    };
  });
}
