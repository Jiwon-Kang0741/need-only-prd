import type { Slots } from 'vue';
import { nextTick, Ref, ref } from 'vue';

export function useCellSelection(
  props: any,
  enableCellSelection: any,
  enableCellRangeSelection: any,
  tableRef: any,
  visibleColumns: any,
  toast: any,
  slots: Slots,
  editingCell: Ref<{ id: string; field: string } | null>
) {
  const selectedCell = ref<{ rowIndex: number; field: string } | null>(null);
  const selectedCellRange = ref<{
    start: { rowIndex: number; field: string };
    end: { rowIndex: number; field: string };
  } | null>(null);

  const editingCellRef = editingCell;

  const highlightSelectedCells = () => {
    const tableEl = tableRef?.value.$el as HTMLElement | undefined;
    if (!tableEl) return;

    const rows = tableEl.querySelectorAll<HTMLTableRowElement>('tbody > tr');
    const fields = visibleColumns.value.map((c: any) => c.field);

    // 전체 초기화
    rows.forEach((tr) => {
      tr.querySelectorAll<HTMLTableCellElement>(
        'td[data-pc-section="bodycell"]'
      ).forEach((td) => td.classList.remove('cell-selected'));

      // 행의 hasSelectedCell 클래스도 제거
      tr.classList.remove('has-selected-cell');
    });

    if (enableCellRangeSelection.value && selectedCellRange.value) {
      // 범위 선택
      const { start, end } = selectedCellRange.value;
      const startRow = Math.min(start.rowIndex, end.rowIndex);
      const endRow = Math.max(start.rowIndex, end.rowIndex);
      const startCol = Math.min(
        fields.indexOf(start.field),
        fields.indexOf(end.field)
      );
      const endCol = Math.max(
        fields.indexOf(start.field),
        fields.indexOf(end.field)
      );

      for (let r = startRow; r <= endRow; r += 1) {
        const row = rows[r];
        if (row) {
          const tds = row.querySelectorAll<HTMLTableCellElement>(
            'td[data-pc-section="bodycell"]'
          );

          let hasSelectedCellInRow = false;
          tds.forEach((td) => {
            const colIdx = fields.indexOf(
              td
                .querySelector('[data-p-field]')
                ?.getAttribute('data-p-field') ?? ''
            );
            if (colIdx >= startCol && colIdx <= endCol) {
              td.classList.add('cell-selected');
              hasSelectedCellInRow = true;
            }
          });

          // 해당 행에 선택된 셀이 있으면 행에도 클래스 추가
          if (hasSelectedCellInRow) {
            row.classList.add('has-selected-cell');
          }
        }
      }
      return; // 조기 종료
    }

    // 단일 선택
    if (selectedCell.value && !selectedCellRange.value) {
      const { rowIndex, field } = selectedCell.value;
      const row = rows[rowIndex];
      if (!row) return;

      const td = Array.from(
        row.querySelectorAll('td[data-pc-section="bodycell"]')
      ).find(
        (tdEl) =>
          tdEl.querySelector('[data-p-field]')?.getAttribute('data-p-field') ===
          field
      );

      td?.classList.add('cell-selected');
      row.classList.add('has-selected-cell');
    }
  };

  const handleCellClick = (
    data: any,
    field: string,
    rowIndex: number,
    event: MouseEvent
  ) => {
    if (data.rowStatus === 'I' || slots[`editor-${field}`]) {
      editingCellRef.value = { id: data.id, field };
    } else {
      editingCellRef.value = null;
    }

    if (!enableCellSelection.value) return;

    if (event.shiftKey && selectedCell.value) {
      // Shift + 클릭: 범위 선택
      selectedCellRange.value = {
        start: { ...selectedCell.value },
        end: { rowIndex, field },
      };
    } else {
      // 단일 셀 선택
      selectedCell.value = { rowIndex, field };
      selectedCellRange.value = null;
    }

    nextTick(() => {
      highlightSelectedCells();
    });
  };

  return {
    selectedCell,
    selectedCellRange,
    handleCellClick,
    highlightSelectedCells,
  };
}
