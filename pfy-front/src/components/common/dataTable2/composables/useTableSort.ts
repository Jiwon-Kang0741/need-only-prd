import orderBy from 'lodash/orderBy';
import { ref } from 'vue';

export type SortOrder = 'asc' | 'desc';
export interface SortMeta {
  field: string;
  order: SortOrder;
}

export function useTableSort() {
  const sortMeta = ref<SortMeta[]>([]);

  const getSortedRows = (rows: any[]) => {
    if (!sortMeta.value.length) return rows;
    const fields = sortMeta.value.map((m) => m.field);
    const orders = sortMeta.value.map((m) => m.order);
    return orderBy(rows, fields, orders);
  };

  const updateSortMeta = (field: string) => {
    const idx = sortMeta.value.findIndex((s) => s.field === field);
    if (idx >= 0) {
      const cur = sortMeta.value[idx];
      if (cur.order === 'asc') sortMeta.value[idx] = { ...cur, order: 'desc' };
      else sortMeta.value.splice(idx, 1);
    } else {
      sortMeta.value.push({ field, order: 'asc' });
    }
  };

  return { sortMeta, getSortedRows, updateSortMeta };
}
