<template>
  <div class="main-content-container">
    <ContentHeader menuId="SCREEN_ID" />

    <TypeDSearchForm @search="handleSearch" />

    <!-- 마스터 테이블 -->
    <section class="table-section">
      <TypeDMasterTable
        :fetchedMasterData="fetchedMasterData"
        :loading="masterLoading"
        @row-select="handleMasterRowSelect"
        @row-dblclick="handleMasterRowDblClick"
      />
    </section>

    <!-- 상세 테이블 -->
    <section class="table-section">
      <TypeDDetailTable
        :fetchedDetailData="fetchedDetailData"
        :loading="detailLoading"
      />
    </section>
  </div>
</template>

<script lang="ts" setup>
import { ref, provide, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue';
import TypeDSearchForm from './components/TypeDSearchForm/TypeDSearchForm.vue';
import TypeDMasterTable from './components/TypeDMasterTable/TypeDMasterTable.vue';
import TypeDDetailTable from './components/TypeDDetailTable/TypeDDetailTable.vue';
import { useAuthenticationStore } from '@/stores/authentication';
import api from '@/plugins/axios';

// ─── Types ───────────────────────────────────────────────────────────────────
export interface SearchParams {
  status?: string | null;
  keyword?: string;
  searchDt?: Date[];
}

export interface MasterData {
  [key: string]: any;
}

export interface DetailData {
  [key: string]: any;
}

// ─── Stores ───────────────────────────────────────────────────────────────────
const toast     = useToast();
const authStore = useAuthenticationStore();

// ─── State ────────────────────────────────────────────────────────────────────
const searchParams      = ref<SearchParams>({ status: null, keyword: '' });
const fetchedMasterData = ref<MasterData[]>([]);
const fetchedDetailData = ref<DetailData[]>([]);
const selectedMaster    = ref<MasterData | null>(null);
const masterLoading     = ref(false);
const detailLoading     = ref(false);

// ─── Provide ─────────────────────────────────────────────────────────────────
provide('searchParams', searchParams);
provide('selectedMaster', selectedMaster);

// ─── API ──────────────────────────────────────────────────────────────────────
const buildCommonParams = () => ({
  gPBL_CD: authStore.pblCd,
  gLANG: authStore.lang,
  gTYPE_CD: authStore.typeCd,
  gCOMP_CD: authStore.compCd,
});

const convertSearchParams = (params: SearchParams): Record<string, any> => {
  const converted: Record<string, any> = buildCommonParams();

  if (params.status)  converted.STATUS  = params.status;
  if (params.keyword) converted.KEYWORD = params.keyword;

  if (params.searchDt?.[0]) {
    const fmt = (d: Date) =>
      `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
    converted.SEARCHDT_FROM = fmt(params.searchDt[0]);
    if (params.searchDt[1]) converted.SEARCHDT_TO = fmt(params.searchDt[1]);
  }

  return converted;
};

const fetchMasterData = async () => {
  try {
    masterLoading.value = true;
    fetchedMasterData.value = [];
    fetchedDetailData.value = [];
    selectedMaster.value    = null;

    // NOTE: API URL을 실제 엔드포인트로 교체하세요
    const response = await api.post('/online/mvcJson/SCREEN_ID-selectMasterList', {
      dsSearch: [convertSearchParams(searchParams.value)],
    });
    fetchedMasterData.value = response.data?.payload?.dsOutput ?? [];
  } catch {
    toast.add({ severity: 'error', summary: '오류', detail: '마스터 데이터 조회 중 오류가 발생했습니다.', life: 3000 });
  } finally {
    masterLoading.value = false;
  }
};

const fetchDetailData = async (masterRow: MasterData) => {
  try {
    detailLoading.value = true;
    fetchedDetailData.value = [];

    // NOTE: 마스터 키 필드명을 실제 필드명으로 교체하세요 (예: MASTER_ID)
    const response = await api.post('/online/mvcJson/SCREEN_ID-selectDetailList', {
      dsSearch: [{
        ...buildCommonParams(),
        MASTER_KEY: masterRow.MASTER_KEY,
      }],
    });
    fetchedDetailData.value = response.data?.payload?.dsOutput ?? [];
  } catch {
    toast.add({ severity: 'error', summary: '오류', detail: '상세 데이터 조회 중 오류가 발생했습니다.', life: 3000 });
  } finally {
    detailLoading.value = false;
  }
};

// ─── Handlers ─────────────────────────────────────────────────────────────────
const handleSearch = async () => {
  await fetchMasterData();
};

const handleMasterRowSelect = async (row: MasterData) => {
  selectedMaster.value = row;
  await fetchDetailData(row);
};

const handleMasterRowDblClick = (row: MasterData) => {
  // NOTE: 더블클릭 시 수정 페이지 이동 또는 Dialog 열기
  console.log('Master row double clicked:', row);
};

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  await fetchMasterData();
});
</script>

<style scoped lang="scss" src="./TypeDScreen.scss"></style>
