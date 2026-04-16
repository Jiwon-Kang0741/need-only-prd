export interface SearchParams {
  status?: string | null;
  keyword?: string;
  searchDt?: Date[];
}

export interface TreeNode {
  key: string;
  label: string;
  data?: Record<string, any>;
  icon?: string;
  children?: TreeNode[];
  leaf?: boolean;
}

export interface MainData {
  [key: string]: any;
}
