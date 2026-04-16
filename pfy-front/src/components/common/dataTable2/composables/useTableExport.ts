import { computed, inject, nextTick, Ref } from 'vue';
import { useRoute } from 'vue-router';

import { fetchFileList } from '@/api/file';
import { FlattenedMenuListItem } from '@/api/menu';
import { SYCC050SelectTmplFileId } from '@/api/pages/sy/cc/sycc050';
import { useAttachments } from '@/composables/useAttachments';
import { useConfirmDialog } from '@/composables/useConfirmDialog';
import { getMsgNm } from '@/composables/useMessage';
import { useToastMessage } from '@/composables/useToastMessage';
import { TableColumn } from '@/types/dataTable';
import { downloadExcel } from '@/utils/excelDownLoad';

export function useTableExport({
  columns,
  data,
  searchConditions,
  onClickDownloadTemplate,
  onBeforeDownloadExcel,
  downloadTemplateInfo,
}: {
  columns: () => TableColumn[];
  data: () => any[];
  searchConditions: () => any[];
  onClickDownloadTemplate?: () => void;
  onBeforeDownloadExcel?: () => Promise<any[]>;
  downloadTemplateInfo?: {
    bizCode: string;
    windowId: string;
    inptSeqNo: number;
  };
}) {
  const { confirm } = useConfirmDialog();
  const { toast } = useToastMessage();

  const route = useRoute();
  const menuList = inject('menuList') as Ref<FlattenedMenuListItem[]>;
  const newTitle = computed(
    () =>
      menuList.value.find((menuItem) => menuItem.menuId === route.meta.menuId)
        ?.menuNm ?? ''
  );

  const handleDownloadExcel = async () => {
    let newData = [];

    if (onBeforeDownloadExcel) {
      newData = await onBeforeDownloadExcel();
    } else {
      newData = data();
    }

    nextTick(async () => {
      confirm({
        message: await getMsgNm('SM0035'),
        acceptLabel: await getMsgNm('CM0054'),
        rejectLabel: await getMsgNm('CM0055'),
        accept: async () => {
          downloadExcel({
            columns: columns(),
            data: newData,
            title: newTitle.value,
            searchConditions: searchConditions(),
          });

          toast({
            severity: 'success',
            summary: 'Success',
            detail: await getMsgNm('CM0052'),
          });
        },
      });
    });
  };

  const { download } = useAttachments(downloadTemplateInfo?.bizCode ?? '');

  const selectFileInfo = async (fileId: string) => {
    const fileList = await fetchFileList(fileId);
    return {
      fileNo: fileList[0].fileNo,
      fileSno: fileList[0].fileSno,
      fileName: fileList[0].fileNm,
    };
  };

  const downloadTemplate = async () => {
    const response = await SYCC050SelectTmplFileId({
      windowId: downloadTemplateInfo?.windowId ?? '',
      inptSeqNo: downloadTemplateInfo?.inptSeqNo || 1,
    });

    if (response.payload.afid) {
      const fileInfo = await selectFileInfo(response.payload.afid);
      await download(fileInfo.fileNo, fileInfo.fileSno, fileInfo.fileName);
    }
  };

  const handleDownloadTemplate = async () => {
    confirm({
      message: await getMsgNm('SM0035'),
      acceptLabel: await getMsgNm('CM0054'),
      rejectLabel: await getMsgNm('CM0055'),
      accept: async () => {
        if (onClickDownloadTemplate) {
          onClickDownloadTemplate?.();
        } else {
          await downloadTemplate();
        }
      },
    });
  };

  return {
    handleDownloadExcel,
    handleDownloadTemplate,
  };
}
