<template>
  <div class="treetable-container">
    <!-- 헤더 (title prop 또는 header 슬롯 사용 시 표시) -->
    <div v-if="$slots.header || title" class="treetable-header">
      <span v-if="title" class="title">{{ title }}</span>
      <slot name="header" />
      <div class="util-buttons">
        <slot name="buttons" />
      </div>
    </div>

    <PrimeTreeTable
      v-model:selectionKeys="selectionKeysModel"
      v-bind="$attrs"
      :value="value"
      :loading="loading"
      :selectionMode="selectionMode"
      :scrollable="scrollable"
      :scrollHeight="scrollHeight"
      :resizableColumns="resizableColumns"
      :columnResizeMode="columnResizeMode"
      :tableStyle="tableStyle"
      class="treetable-root"
      @node-select="(node) => emit('node-select', node)"
      @node-unselect="(node) => emit('node-unselect', node)"
      @node-expand="(node) => emit('node-expand', node)"
      @node-collapse="(node) => emit('node-collapse', node)"
    >
      <!-- columns prop 사용 시 동적 컬럼 렌더링 -->
      <template v-if="columns?.length">
        <PrimeColumn
          v-for="col in visibleColumns"
          :key="col.objectId"
          :field="col.field"
          :header="col.header"
          :expander="col.expander ?? false"
          :frozen="col.frozen ?? false"
          :style="col.width && col.width !== 'auto' ? { width: col.width } : undefined"
          :headerClass="col.columnClass ?? 'center'"
          :bodyClass="col.rowClass ?? 'center'"
        >
          <template #header>
            <span class="column-content">{{ col.header }}</span>
          </template>
          <template #body="{ node }">
            <slot :name="`body-${col.field}`" :node="node" :data="node.data">
              {{ node.data?.[col.field] ?? '' }}
            </slot>
          </template>
        </PrimeColumn>
      </template>

      <!-- 슬롯으로 Column 직접 지정할 때 -->
      <slot v-else />

      <!-- 빈 데이터 -->
      <template #empty>
        <div class="empty-msg">
          <i class="pi pi-inbox icon" />
          <span>{{ emptyMessage }}</span>
        </div>
      </template>
    </PrimeTreeTable>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue';
import PrimeTreeTable from 'primevue/treetable';
import PrimeColumn from 'primevue/column';
import type { TreeNode } from 'primevue/treenode';

import type { TreeTableColumn, TreeTableSelectionKeys } from './types';

/** 루트 div가 아닌 PrimeTreeTable으로 v-model:expandedKeys 등 $attrs 를 넘기기 위해 */
defineOptions({ inheritAttrs: false });

// ─── Props ────────────────────────────────────────────────────────────────────
interface Props {
  value?: TreeNode[];
  columns?: TreeTableColumn[];
  loading?: boolean;
  selectionMode?: 'single' | 'multiple' | 'checkbox';
  scrollable?: boolean;
  scrollHeight?: string;
  resizableColumns?: boolean;
  columnResizeMode?: 'fit' | 'expand';
  tableStyle?: string;
  title?: string;
  emptyMessage?: string;
}

const props = withDefaults(defineProps<Props>(), {
  value: () => [],
  columns: () => [],
  loading: false,
  selectionMode: undefined,
  scrollable: true,
  scrollHeight: 'flex',
  resizableColumns: false,
  columnResizeMode: 'fit',
  emptyMessage: '데이터가 없습니다.',
});

// ─── Emits ────────────────────────────────────────────────────────────────────
const emit = defineEmits<{
  (e: 'node-select', node: TreeNode): void;
  (e: 'node-unselect', node: TreeNode): void;
  (e: 'node-expand', node: TreeNode): void;
  (e: 'node-collapse', node: TreeNode): void;
  (e: 'update:selectionKeys', keys: TreeTableSelectionKeys): void;
}>();

// ─── v-model ─────────────────────────────────────────────────────────────────
const selectionKeysModel = defineModel<TreeTableSelectionKeys>('selectionKeys');

// ─── Computed ─────────────────────────────────────────────────────────────────
const visibleColumns = computed(() =>
  props.columns.filter((col) => col.visible !== false)
);
</script>

<style scoped lang="scss" src="./treeTable.scss"></style>
