<template>
  <div class="datatable-wrapper">
    <!-- DataTable 헤더: 제목 + 건수 + 액션 버튼 -->
    <div class="datatable-header">
      <div class="title">
        목록
        <div class="count">
          총 <span class="total">{{ processedData.length }}</span>건 /
          선택 <span class="num">{{ selectedRows.length }}</span>건
        </div>
      </div>
      <div class="action-group-wrapper">
        <div class="action-group">
          <Button icon="pi pi-refresh" variant="text" size="small" rounded />
          <Button icon="pi pi-download" variant="text" size="small" rounded />
        </div>
        <div class="action-group">
          <Button label="신규" icon="pi pi-plus" size="small" />
          <Button label="저장" icon="pi pi-save" size="small" severity="secondary" />
          <Button label="삭제" icon="pi pi-trash" size="small" variant="outlined" />
        </div>
      </div>
    </div>

    <!-- DataTable -->
    <DataTable
      class="datatable-root"
      v-model:selection="selectedRows"
      :value="processedData"
      :loading="loading"
      scrollable
      scrollHeight="flex"
      :virtualScrollerOptions="{ itemSize: 46 }"
      selectionMode="multiple"
      dataKey="ITEM_NO"
      stripedRows
      showGridlines
      @row-dblclick="handleRowDblClick"
    >
      <!-- 체크박스 컬럼 -->
      <Column selectionMode="multiple" frozen headerStyle="width: 3rem" />

      <!-- 동적 컬럼 렌더링 -->
      <Column
        v-for="col in columns"
        :key="col.field"
        :field="col.field"
        :header="col.header"
        :style="col.style"
        :frozen="col.frozen ?? false"
        :headerClass="col.headerClass ?? ''"
        :bodyClass="col.bodyClass ?? ''"
      />
    </DataTable>

    <!-- Paginator -->
    <Paginator
      :rows="pageRows"
      :totalRecords="processedData.length"
      :rowsPerPageOptions="[10, 20, 50, 100]"
      @page="onPageChange"
    />
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, watch, nextTick } from 'vue';
import { DataTable } from '@/components/common/dataTable2';
import { Button } from '@/components/common/button';
import Paginator from '@/components/common/paginator/Paginator.vue';
import Column from 'primevue/column';
import type { MainData } from '../../index.vue';
import { getColumns, getRows } from './utils/index';

// ─── Props ────────────────────────────────────────────────────────────────────
interface Props {
  fetchedMainData: MainData[];
  loading: boolean;
}

const props = defineProps<Props>();

// ─── Emits ───────────────────────────────────────────────────────────────────
const emit = defineEmits<{
  (e: 'row-dblclick', row: MainData): void;
}>();

// ─── State ────────────────────────────────────────────────────────────────────
const selectedRows = ref<MainData[]>([]);
const processedData = ref<MainData[]>([]);
const pageRows = ref(20);

// ─── 컬럼 정의 ────────────────────────────────────────────────────────────────
const columns = computed(() => getColumns());

// ─── 날짜 포맷팅 전처리 (성능 최적화 - 템플릿 슬롯 방식 대신 watch 사용) ─────────
watch(
  () => props.fetchedMainData,
  async (newData) => {
    if (!newData) {
      processedData.value = [];
      return;
    }
    await nextTick();
    processedData.value = getRows(newData);
  },
  { immediate: true }
);

// ─── Handlers ─────────────────────────────────────────────────────────────────
const handleRowDblClick = (event: any) => {
  emit('row-dblclick', event.data);
};

const onPageChange = (event: any) => {
  pageRows.value = event.rows;
};

// ─── Expose ──────────────────────────────────────────────────────────────────
defineExpose({ selectedRows });
</script>

<style scoped lang="scss" src="./TypeADataTable.scss"></style>
