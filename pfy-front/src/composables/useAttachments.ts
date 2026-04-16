import { ref } from 'vue';

import {
  fetchFileDelete,
  fetchFileDownload,
  fetchFileList,
  fetchUploadFiles,
  fetchZipDownload,
} from '@/api/file';

type AttachItem = {
  id: number;
  name: string;
  url: string;
  fileNo: string;
};

export function useAttachments(bizCode: string) {
  const lastFileNo = ref<string | null>(null);
  const items = ref<AttachItem[]>([]);

  const load = async (fileNos: string | string[] | null) => {
    if (!fileNos || (Array.isArray(fileNos) && fileNos.length === 0)) {
      items.value = [];
      return;
    }

    const list = await fetchFileList(fileNos);
    const mapped: AttachItem[] = list.map((s: any) => ({
      id: s.fileSno,
      name: s.fileNm,
      url: s.fileUrl ?? '',
      fileNo: s.fileNo,
    }));

    items.value = mapped;
    lastFileNo.value = mapped[0]?.fileNo ?? lastFileNo.value;
  };

  async function upload(files: File[], groupFileNo?: string | null) {
    const continueGroup = groupFileNo ?? lastFileNo.value ?? undefined;
    const res = await fetchUploadFiles(files, bizCode, continueGroup);
    const uploaded = res?.uploadedFiles ?? [];

    if (!uploaded.length) return [];

    const mapped: AttachItem[] = uploaded.map((s: any) => ({
      id: s.fileSno,
      name: s.fileNm,
      url: s.fileUrl ?? '', // 임시 파일 접근 URL
      fileNo: s.fileNo,
    }));

    // 조회 안 되는 파일이므로 local items에 강제로 추가
    items.value = [
      ...items.value,
      ...mapped.filter(
        (m) => !items.value.some((i) => i.id === m.id && i.fileNo === m.fileNo)
      ),
    ];

    lastFileNo.value = uploaded[0]?.fileNo ?? lastFileNo.value;

    // payload에는 fileNo만 필요
    const newFileNos = Array.from(
      new Set(uploaded.map((s) => s.fileNo).filter(Boolean))
    );

    return newFileNos;
  }

  const remove = async (fileNo: string, fileSno: number) => {
    items.value = items.value.filter(
      (i) => !(i.fileNo === fileNo && i.id === fileSno)
    );

    try {
      await fetchFileDelete(fileNo, fileSno);

      const fileNos = Array.from(new Set(items.value.map((i) => i.fileNo)));
      if (fileNos.length) {
        await load(fileNos);
      } else {
        items.value = [];
        lastFileNo.value = null;
      }
    } catch (err) {
      await load(fileNo);
      throw err;
    }
  };

  async function download(
    fileNo: string,
    fileSno: number,
    filename?: string
  ) {
    const blob = await fetchFileDownload(fileNo, fileSno);
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `download-${fileSno}`;
    a.click();

    URL.revokeObjectURL(url);
  }

  const zipDownload = async (
    files: { fileNo: string; fileSno: number }[],
    filename = 'attachments.zip'
  ) => {
    if (!files?.length) return;
    const blob = await fetchZipDownload(files);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename.endsWith('.zip') ? filename : `${filename}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const fileNo = lastFileNo;

  return {
    fileNo,
    lastFileNo,
    items,
    load,
    upload,
    remove,
    download,
    zipDownload,
  };
}
