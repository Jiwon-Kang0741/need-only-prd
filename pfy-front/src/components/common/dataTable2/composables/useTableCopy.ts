import { computed, Ref } from 'vue';

import { extractCellText } from '@/components/common/dataTable2/utils/extractCellText';
import { getMsgNm } from '@/composables/useMessage';
import { useToastMessage } from '@/composables/useToastMessage';

export function useTableCopy({
  tableId,
  tableRef,
  enableCellSelection,
}: {
  tableId: string;
  tableRef: Ref<any>;
  enableCellSelection: Ref<boolean>;
}) {
  const { toast } = useToastMessage();
  const isCellSelectionMode = computed(() => enableCellSelection.value);

  const isEditable = (el: HTMLElement | null): boolean => {
    if (!el) return false;
    return (
      el.tagName === 'INPUT' ||
      el.tagName === 'TEXTAREA' ||
      el.isContentEditable ||
      !!el.closest(
        '.p-inputtext, .p-inputtextarea, .p-dropdown, .p-multiselect, .p-autocomplete,' +
          '.tiptap, [role="textbox"], [role="combobox"], [contenteditable=""], [contenteditable="true"]'
      )
    );
  };

  const handleRowTextCopy = () => {
    if (isCellSelectionMode.value) return;

    const tableElement = tableRef.value?.$el;
    if (!tableElement) return;

    const tbody = tableElement.querySelector('tbody');
    if (!tbody) return;

    const selectedRowElements = tbody.querySelectorAll(
      'tr.p-datatable-selectable-row.p-datatable-row-selected'
    );
    if (selectedRowElements.length === 0) return;

    const lines: string[] = [];

    selectedRowElements.forEach((row: Element) => {
      const cellTexts: string[] = [];

      // 데이터 셀만 선택 (시스템 컬럼 제외)
      const dataCells = row.querySelectorAll('td[data-pc-section="bodycell"]');

      dataCells.forEach((cell: Element) => {
        const textContent = extractCellText(cell);
        cellTexts.push(textContent);
      });

      if (cellTexts.length > 0) {
        lines.push(cellTexts.join('\t'));
      }
    });

    if (lines.length > 0) {
      navigator.clipboard.writeText(lines.join('\n')).then(async () => {
        toast({
          severity: 'success',
          summary: 'Success',
          detail: await getMsgNm('CM0063'),
        });
      });
    }
  };

  const handleCellTextCopy = () => {
    const tableElement = tableRef.value?.$el;
    if (!tableElement) return;

    const tbody = tableElement.querySelector('tbody');
    if (!tbody) return;

    const selectedCells = tbody.querySelectorAll('td.cell-selected');

    if (selectedCells.length === 0) return;

    // 단일 셀 복사
    if (selectedCells.length === 1) {
      const textContent = extractCellText(selectedCells[0]);

      if (textContent) {
        navigator.clipboard.writeText(textContent).then(async () => {
          toast({
            severity: 'success',
            summary: 'Success',
            detail: await getMsgNm('CM0063'),
          });
        });
      }
      return;
    }

    // 다중 셀/범위 복사
    const selectedRows = tbody.querySelectorAll('tr.has-selected-cell');
    const copied: string[] = [];

    selectedRows.forEach((row: Element) => {
      const cellsInRow = row.querySelectorAll('td.cell-selected');
      if (cellsInRow.length > 0) {
        const line: string[] = [];

        const allCells = row.querySelectorAll('td[data-pc-section="bodycell"]');
        allCells.forEach((cell: Element) => {
          if (cell.classList.contains('cell-selected')) {
            const textContent = extractCellText(cell);
            line.push(textContent);
          }
        });

        if (line.length > 0) {
          copied.push(line.join('\t'));
        }
      }
    });

    if (copied.length > 0) {
      navigator.clipboard.writeText(copied.join('\n')).then(async () => {
        toast({
          severity: 'success',
          summary: 'Success',
          detail: await getMsgNm('CM0063'),
        });
      });
    }
  };

  const handleCopy = (e: ClipboardEvent) => {
    const target = e.target as HTMLElement | null;

    // 현재 테이블 내부 클릭인지 확인 (고유 ID로 식별)
    const currentTable = target?.closest(`[data-table-id="${tableId}"]`);
    if (!currentTable) return;

    // 1) 입력/에디터라면 기본 복사 허용
    if (isEditable(target)) return;

    // 2) 사용자가 드래그로 텍스트 선택 중이면 기본 복사 허용
    if (window.getSelection()?.toString()) return;

    // 3) 여기서만 커스텀 복사
    e.preventDefault();

    if (isCellSelectionMode.value) {
      handleCellTextCopy();
    } else {
      handleRowTextCopy();
    }
  };

  return {
    handleCopy,
  };
}
