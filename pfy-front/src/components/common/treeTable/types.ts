export type TreeTableSelectionKeys = Record<
  string,
  { partialChecked: boolean; checked: boolean }
>;

export type TreeTableColumn = {
  objectId: string;
  field: string;
  header: string;
  width?: string;
  columnClass?: string;
  rowClass?: string;
  visible?: boolean;
  frozen?: boolean;
  expander?: boolean;
};
