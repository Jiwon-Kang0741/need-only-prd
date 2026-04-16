<template>
  <div class="main-content-container">
    <ContentHeader menuId="SCREEN_ID" />

    <TypeASearchForm @search="handleSearch" />

    <TypeADataTable
      :fetchedMainData="fetchedMainData"
      :loading="loading"
    />
  </div>
</template>

<script lang="ts" setup>
import { ref, provide, onMounted } from 'vue';
import type { Ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue';
import TypeASearchForm from './components/TypeASearchForm/TypeASearchForm.vue';
import TypeADataTable from './components/TypeADataTable/TypeADataTable.vue';
import { useAuthenticationStore } from '@/stores/authentication';
import api from '@/plugins/axios';

// ─── Types ───────────────────────────────────────────────────────────────────
// NOTE: 실제 프로젝트에서는 @/api/pages/[module]/[category]/types.ts 에 정의
export interface SearchParams {
  status?: string | null;
  keyword?: string;
  searchDtType?: string;
  searchDt?: Date[];
  SEARCHDT_FROM?: string;
  SEARCHDT_TO?: string;
}

export interface MainData {
  [key: string]: any;
}

// ─── Stores / Utils ───────────────────────────────────────────────────────────
const toast = useToast();
const authStore = useAuthenticationStore();

// ─── State ────────────────────────────────────────────────────────────────────
const searchParams = ref<SearchParams>({
  status: null,
  keyword: '',
  searchDtType: 'default',
  searchDt: [],
});

const fetchedMainData = ref<MainData[]>([]);
const loading = ref(false);

// ─── Provide ─────────────────────────────────────────────────────────────────
provide('searchParams', searchParams);

// ─── API ──────────────────────────────────────────────────────────────────────
const convertParams = (params: SearchParams): Record<string, any> => {
  const converted: Record<string, any> = {
    gPBL_CD: authStore.pblCd,
    gLANG: authStore.lang,
    gTYPE_CD: authStore.typeCd,
    gCOMP_CD: authStore.compCd,
  };

  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      converted[key.toUpperCase()] = value;
    }
  }

  if (params.searchDt && Array.isArray(params.searchDt) && params.searchDt[0]) {
    const fmt = (d: Date) =>
      `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
    converted.SEARCHDT_FROM = fmt(params.searchDt[0]);
    if (params.searchDt[1]) converted.SEARCHDT_TO = fmt(params.searchDt[1]);
  }

  delete converted.SEARCHDT;

  return converted;
};

const fetchMainData = async () => {
  try {
    loading.value = true;
    // NOTE: API URL을 실제 엔드포인트로 교체하세요
    const response = await api.post('/online/mvcJson/SCREEN_ID-selectList', {
      dsSearch: [convertParams(searchParams.value)],
    });
    fetchedMainData.value = response.data?.payload?.dsOutput ?? [];
  } catch (err: any) {
    toast.add({ severity: 'error', summary: '오류', detail: '데이터 조회 중 오류가 발생했습니다.', life: 3000 });
  } finally {
    loading.value = false;
  }
};

// ─── Handlers ─────────────────────────────────────────────────────────────────
const handleSearch = async () => {
  await fetchMainData();
};

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  await fetchMainData();
});
</script>

<style scoped lang="scss" src="./TypeAScreen.scss"></style>
