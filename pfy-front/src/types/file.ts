export interface FileItem {
  fileNo: string;
  fileSno: number;
  filePath: string;
  fileTypeCd: string;
  svflNm: string; // 서버 저장 파일명
  fileNm: string; // 원본 파일명
  fileExtnsnNm: string; // 확장자
  flszQnty: number; // 파일 크기
  refNo: string | null;
  busnNm: string | null;
  btbStoreYn: string | null;
  useYn: 'Y' | 'N';
  fstCrtrId: string;
  fstCretDtm: string;
  lastMdfrId: string;
  lastMdfcDtm: string;
}

export interface UploadResponse {
  uploadedFiles: FileItem[];
  errors: any | null;
  successCount: number;
  totalCount: number;
}

export type FileListResponse = FileItem[];
