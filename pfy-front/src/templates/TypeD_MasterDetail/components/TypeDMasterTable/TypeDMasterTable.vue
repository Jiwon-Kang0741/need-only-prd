<template>
  <div class="datatable-wrapper">
    <!-- DataTable 헤더: 제목 + 건수 + 액션 버튼 -->
    <div class="datatable-header">
      <div class="title">
        마스터 목록
        <div class="count">
          총 <span class="total">{{ processedData.length }}</span>건 /
          선택 <span class="num">{{ selectedRow ? 1 : 0 }}</span>건
        </div>
      </div>
      <div class="action-group-wrapper">
        <div class="action-group">
          <Button icon="pi pi-refresh" variant="text" size="small" rounded />
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
      v-model:selection="selectedRow"
      :value="processedData"
      :loading="loading"
      scrollable
      scrollHeight="flex"
      :virtualScrollerOptions="{ itemSize: 46 }"
      selectionMode="single"
      dataKey="MASTER_KEY"
      :metaKeySelection="false"
      stripedRows
      showGridlines
      @row-select="handleRowSelect"
      @row-dblclick="handleRowDblClick"
    >
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
      :rowsPerPageOptions="[10, 20, 50]"
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
import type { MasterData } from '../../index.vue';
import { getMasterColumns, getMasterRows } from './utils/index';

interface Props {
  fetchedMasterData: MasterData[];
  loading: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'row-select', row: MasterData): void;
  (e: 'row-dblclick', row: MasterData): void;
}>();

const selectedRow   = ref<MasterData | null>(null);
const processedData = ref<MasterData[]>([]);
const columns       = computed(() => getMasterColumns());
const pageRows      = ref(20);

watch(
  () => props.fetchedMasterData,
  async (newData) => {
    if (!newData) { processedData.value = []; return; }
    await nextTick();
    processedData.value = getMasterRows(newData);
    selectedRow.value   = null;
  },
  { immediate: true }
);

const handleRowSelect   = (event: any) => emit('row-select', event.data);
const handleRowDblClick = (event: any) => emit('row-dblclick', event.data);

const onPageChange = (event: any) => {
  pageRows.value = event.rows;
};

defineExpose({ selectedRow });
</script>

<style scoped lang="scss" src="./TypeDMasterTable.scss"></style>
