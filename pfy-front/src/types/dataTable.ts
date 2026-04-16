export enum EditorType {
  Text = 'text',
  Select = 'select',
  Checkbox = 'checkbox',
}

// datatable column type
export type TableColumn = {
  objectId: string;
  field: string;
  header: string;
  width?: string;
  columnClass?: string;
  rowClass?: string;
  visible?: boolean;
  frozen?: boolean;
};

// datatable util buttons type
export type UtilButton = {
  type: string;
  objectId: string;
  used: boolean;
  disabled?: boolean;
};
