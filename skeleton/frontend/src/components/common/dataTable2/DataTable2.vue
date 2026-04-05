<template>
  <div class="data-table-wrapper">
    <DataTable
      :value="value || []"
      :loading="loading"
      :paginator="paginator"
      :rows="rows || 10"
      :totalRecords="totalRecords"
      :scrollable="true"
      :scrollHeight="scrollHeight || '540px'"
      :virtualScrollerOptions="virtualScrollerOptions || { itemSize: 46 }"
      :selectionMode="selectionMode"
      :selection="selection"
      :dataKey="dataKey || 'id'"
      stripedRows
      showGridlines
      responsiveLayout="scroll"
      @page="$emit('page', $event)"
      @row-click="$emit('row-click', $event)"
      @row-select="$emit('row-select', $event)"
      @row-unselect="$emit('row-unselect', $event)"
      @row-select-all="$emit('row-select-all', $event)"
      @row-unselect-all="$emit('row-unselect-all', $event)"
      @update:selection="$emit('update:selection', $event)"
    >
      <template #empty>
        <div class="empty-message">
          <i class="pi pi-inbox" style="font-size: 2rem; color: var(--text-3, #868e96);" />
          <p>데이터가 없습니다</p>
        </div>
      </template>
      <template #loading>
        <div class="loading-message">데이터를 불러오는 중...</div>
      </template>

      <!-- Auto-generate columns from prop -->
      <Column
        v-if="selectionMode === 'multiple'"
        selectionMode="multiple"
        frozen
        headerStyle="width: 3rem"
      />
      <template v-if="columns && columns.length">
        <Column
          v-for="col in columns"
          :key="col.field"
          :field="col.field"
          :header="col.header"
          :sortable="col.sortable !== false"
          :style="col.style"
          :frozen="col.frozen"
          :headerClass="col.headerClass"
          :bodyClass="col.bodyClass"
        />
      </template>

      <!-- Pass through slots for custom columns -->
      <slot />
    </DataTable>
  </div>
</template>

<script setup lang="ts">
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

interface ColumnDef {
  field: string
  header: string
  sortable?: boolean
  style?: string
  frozen?: boolean
  headerClass?: string
  bodyClass?: string
}

defineProps<{
  value?: unknown[]
  columns?: ColumnDef[]
  loading?: boolean
  paginator?: boolean
  rows?: number
  totalRecords?: number
  scrollHeight?: string
  virtualScrollerOptions?: Record<string, unknown>
  selectionMode?: 'single' | 'multiple'
  selection?: unknown
  dataKey?: string
}>()

defineEmits<{
  page: [event: unknown]
  'row-click': [event: unknown]
  'row-select': [event: unknown]
  'row-unselect': [event: unknown]
  'row-select-all': [event: unknown]
  'row-unselect-all': [event: unknown]
  'update:selection': [value: unknown]
}>()
</script>

<style scoped>
.data-table-wrapper {
  background: var(--bg-1, #fff);
  border-radius: var(--border-radius-lg, 12px);
  border: 1px solid var(--border-1, #dee2e6);
  overflow: hidden;
}
.empty-message {
  display: flex; flex-direction: column; align-items: center;
  gap: 8px; padding: 40px; color: var(--text-3, #868e96);
}
.empty-message p { margin: 0; font-size: 14px; }
.loading-message { text-align: center; padding: 20px; color: var(--text-3, #868e96); }
</style>
