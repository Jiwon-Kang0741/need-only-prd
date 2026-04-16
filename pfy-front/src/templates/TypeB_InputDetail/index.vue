<template>
  <div class="main-content-container">
    <ContentHeader menuId="SCREEN_ID" />

    <div class="form-page-wrapper">
      <TypeBInputForm
        :formData="formData"
        :isEditMode="isEditMode"
        :loading="loading"
        @save="handleSave"
        @cancel="handleCancel"
        @reset="handleReset"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useConfirm } from 'primevue/useconfirm';
import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue';
import TypeBInputForm from './components/TypeBInputForm/TypeBInputForm.vue';
import { useAuthenticationStore } from '@/stores/authentication';
import api from '@/plugins/axios';

// ─── Types ───────────────────────────────────────────────────────────────────
// NOTE: 실제 프로젝트에서는 @/api/pages/[module]/[category]/types.ts 에 정의
export interface FormData {
  id?: string;
  itemNo?: string;
  itemNm?: string;
  qty?: number;
  status?: string;
  startDt?: Date | null;
  endDt?: Date | null;
  isApproved?: boolean;
  remark?: string;
  attachments?: any[];
  [key: string]: any;
}

// ─── Stores / Router ─────────────────────────────────────────────────────────
const router  = useRouter();
const route   = useRoute();
const toast   = useToast();
const confirm = useConfirm();
const authStore = useAuthenticationStore();

// ─── State ────────────────────────────────────────────────────────────────────
const isEditMode = ref(false);
const loading    = ref(false);
const formData   = ref<FormData>({
  qty: 0,
  isApproved: false,
  attachments: [],
});

// ─── API ──────────────────────────────────────────────────────────────────────
const fetchDetail = async (id: string) => {
  try {
    loading.value = true;
    // NOTE: API URL을 실제 엔드포인트로 교체하세요
    const response = await api.post('/online/mvcJson/SCREEN_ID-selectDetail', {
      dsSearch: [{ ID: id, gPBL_CD: authStore.pblCd, gLANG: authStore.lang }],
    });
    const payload = response.data?.payload?.dsOutput?.[0];
    if (payload) {
      formData.value = { ...payload };
    }
  } catch {
    toast.add({ severity: 'error', summary: '오류', detail: '데이터 조회 중 오류가 발생했습니다.', life: 3000 });
  } finally {
    loading.value = false;
  }
};

const saveData = async (data: FormData) => {
  const endpoint = isEditMode.value
    ? '/online/mvcJson/SCREEN_ID-processUpdate'
    : '/online/mvcJson/SCREEN_ID-processInsert';

  const response = await api.post(endpoint, {
    dsSave: [{
      ...data,
      gPBL_CD: authStore.pblCd,
      gLANG: authStore.lang,
    }],
  });

  if (response.data?.header?.responseCode !== 'S0000') {
    throw new Error(response.data?.header?.responseMessage ?? '저장 실패');
  }
};

// ─── Handlers ─────────────────────────────────────────────────────────────────
const handleSave = async (data: FormData) => {
  confirm.require({
    message: isEditMode.value ? '수정하시겠습니까?' : '등록하시겠습니까?',
    header: '확인',
    acceptLabel: '확인',
    rejectLabel: '취소',
    accept: async () => {
      try {
        loading.value = true;
        await saveData(data);
        toast.add({ severity: 'success', summary: '완료', detail: isEditMode.value ? '수정되었습니다.' : '등록되었습니다.', life: 3000 });
        router.back();
      } catch (err: any) {
        toast.add({ severity: 'error', summary: '오류', detail: err.message ?? '저장 중 오류가 발생했습니다.', life: 3000 });
      } finally {
        loading.value = false;
      }
    },
  });
};

const handleCancel = () => {
  confirm.require({
    message: '입력한 내용이 저장되지 않습니다. 돌아가시겠습니까?',
    header: '확인',
    acceptLabel: '확인',
    rejectLabel: '취소',
    accept: () => router.back(),
  });
};

const handleReset = () => {
  formData.value = { qty: 0, isApproved: false, attachments: [] };
};

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  const id = route.params.id as string;
  if (id) {
    isEditMode.value = true;
    await fetchDetail(id);
  }
});
</script>

<style scoped lang="scss" src="./TypeBScreen.scss"></style>
