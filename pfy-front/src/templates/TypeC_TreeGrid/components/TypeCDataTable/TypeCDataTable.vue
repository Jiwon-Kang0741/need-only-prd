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
      class="datatable-root type-c-datatable"
      v-model:selection="selectedRows"
      :value="processedData"
      :loading="loading"
      scrollable
      :scrollHeight="tableScrollHeight"
      selectionMode="multiple"
      dataKey="ITEM_NO"
      stripedRows
      showGridlines
      @row-dblclick="handleRowDblClick"
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
import type { MainData } from '../../types';
import { getColumns, getRows } from './utils/index';

interface Props {
  fetchedMainData: MainData[];
  loading: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'row-dblclick', row: MainData): void;
}>();

const selectedRows  = ref<MainData[]>([]);
const processedData = ref<MainData[]>([]);
const columns       = computed(() => getColumns());
const pageRows      = ref(20);

/** 부모(.datatable-wrapper)가 height:100%이고 DataTable 자체는 flex:1 이므로 flex 사용 */
const tableScrollHeight = 'flex';

watch(
  () => props.fetchedMainData,
  async (newData) => {
    if (!newData) { processedData.value = []; return; }
    await nextTick();
    processedData.value = getRows(newData);
  },
  { immediate: true }
);

const handleRowDblClick = (event: any) => emit('row-dblclick', event.data);

const onPageChange = (event: any) => {
  pageRows.value = event.rows;
};

defineExpose({ selectedRows });
</script>

<style scoped lang="scss" src="./TypeCDataTable.scss"></style>
