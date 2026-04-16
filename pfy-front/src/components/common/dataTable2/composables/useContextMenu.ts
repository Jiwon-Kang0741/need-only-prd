import { type Ref, ref } from 'vue';

type EmitFn = (event: 'update:selection', ...args: any[]) => void;

interface UseContextMenuOptions {
  contextRow: Ref<any>;
  contextCol: Ref<any>;
  handleCellClick: (
    rowData: any,
    field: string,
    rowIndex: number,
    event: MouseEvent
  ) => void;
  rowCellSelection: Ref<string>;
  emit: EmitFn;
}

export function useContextMenu(options: UseContextMenuOptions) {
  const { handleCellClick, rowCellSelection, emit, contextRow, contextCol } =
    options;

  const menuModel = ref([
    { separator: true },
    {
      label: '셀 선택',
      command: () => {
        // rowCellSelection 값 업데이트로 DataTable의 watch 트리거
        rowCellSelection.value = 'cellSingle';

        const row = contextRow.value;
        const col = contextCol.value;
        if (row && col?.field) {
          handleCellClick(
            row,
            col.field,
            row.rowIndex,
            new MouseEvent('click')
          );
        }
      },
    },
    {
      label: '영역 선택',
      command: () => {
        // rowCellSelection 값 업데이트로 DataTable의 watch 트리거
        rowCellSelection.value = 'cellMultiple';

        const row = contextRow.value;
        const col = contextCol.value;
        if (row && col?.field) {
          handleCellClick(
            row,
            col.field,
            row.rowIndex,
            new MouseEvent('click')
          );
        }
      },
    },
    {
      label: '행 선택',
      command: () => {
        // rowCellSelection 값 업데이트로 DataTable의 watch 트리거
        rowCellSelection.value = 'rowSingle';

        const row = contextRow.value;
        if (row) emit('update:selection', row);
      },
    },
    {
      label: '다중 행 선택',
      command: () => {
        // rowCellSelection 값 업데이트로 DataTable의 watch 트리거
        rowCellSelection.value = 'rowMultiple';
      },
    },
    {
      label: '내용 복사',
      command: () => {
        document.execCommand('copy');
      },
    },
  ]);

  return {
    menuModel,
  };
}
