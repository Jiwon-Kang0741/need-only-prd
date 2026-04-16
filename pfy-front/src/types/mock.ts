export type FieldGenerator = (index: number) => any;

export type FieldMap = Record<string, FieldGenerator>;

export interface MockSchema {
  columnHeaders: { [key: string]: string };
  rows: FieldMap[];
}
