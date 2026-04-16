export const getRowIndex = ({
  rows,
  currentPage,
  pageSize,
  totalElements,
}: {
  rows: any[];
  currentPage: number;
  pageSize: number;
  totalElements: number;
}): any[] => {
  const startIndex = (currentPage - 1) * pageSize;

  return rows.map((row, idx) => {
    const reverseIndex = totalElements - (startIndex + idx);
    return {
      ...row,
      rowIndex: reverseIndex,
    };
  });
};
