// Column definition for the DataTable2 wrapper (FrontendGuide 04 §TableColumn).
export type TableColumn = {
  objectId: string;     // required — same value as field
  field: string;
  header: string;
  width?: string;       // e.g. "140px" (not minWidth)
  columnClass?: string; // header align: 'left' | 'center' | 'right'
  rowClass?: string;    // body cell align
  visible?: boolean;    // required — set true to show the column
  frozen?: boolean;
  required?: boolean;
};
