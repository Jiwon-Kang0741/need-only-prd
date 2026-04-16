<template>
  <div class="datatable-wrapper">
    <!-- DataTable 헤더: 제목 + 건수 + 액션 버튼 -->
    <div class="datatable-header">
      <div class="title">
        상세 목록
        <div class="count">
          총 <span class="total">{{ processedData.length }}</span>건 /
          선택 <span class="num">{{ selectedRows.length }}</span>건
        </div>
      </div>
      <div class="action-group-wrapper">
        <div class="action-group">
          <Button icon="pi pi-refresh" variant="text" size="small" rounded />
        </div>
        <div class="action-group">
          <Button label="행추가" icon="pi pi-plus" size="small" />
          <Button label="저장" icon="pi pi-save" size="small" severity="secondary" />
          <Button label="행삭제" icon="pi pi-trash" size="small" variant="outlined" />
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
      dataKey="DETAIL_KEY"
      stripedRows
      showGridlines
    >
      <Column selectionMode="multiple" frozen headerStyle="width: 3rem" />

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
import type { DetailData } from '../../index.vue';
import { getDetailColumns, getDetailRows } from './utils/index';

interface Props {
  fetchedDetailData: DetailData[];
  loading: boolean;
}

const props = defineProps<Props>();

const selectedRows  = ref<DetailData[]>([]);
const processedData = ref<DetailData[]>([]);
const columns       = computed(() => getDetailColumns());
const pageRows      = ref(20);

watch(
  () => props.fetchedDetailData,
  async (newData) => {
    if (!newData) { processedData.value = []; return; }
    await nextTick();
    processedData.value = getDetailRows(newData);
    selectedRows.value  = [];
  },
  { immediate: true }
);

const onPageChange = (event: any) => {
  pageRows.value = event.rows;
};

defineExpose({ selectedRows });
</script>

<style scoped lang="scss" src="./TypeDDetailTable.scss"></style>
