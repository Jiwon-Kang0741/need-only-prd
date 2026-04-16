<template>
  <div class="type-c-tree">
    <TreeTable
      v-model:expandedKeys="expandedKeys"
      :value="treeTableNodes"
      :columns="columns"
      :loading="loading"
      title="메뉴 목록"
      selectionMode="single"
      v-model:selectionKeys="selectionKeys"
      scrollHeight="flex"
      @node-select="handleNodeSelect"
      @node-unselect="handleNodeUnselect"
    >
      <template #buttons>
        <Button
          label="접기"
          size="small"
          variant="outlined"
          @click="collapseAll"
        />
        <Button
          label="저장"
          size="small"
          @click="onSaveClick"
        />
      </template>

      <template #body-menuNm="{ node, data }">
        <i
          :class="[
            node.children?.length ? 'pi pi-folder' : 'pi pi-file',
            'folder-icon',
          ]"
        />
        <span class="menu-nm-text">{{ data?.menuNm ?? data?.nodeName ?? '' }}</span>
      </template>
    </TreeTable>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, watch } from 'vue';
import type { TreeNode as PrimeTreeNode } from 'primevue/treenode';
import { useToast } from 'primevue/usetoast';
import { TreeTable } from '@/components/common/treeTable';
import type { TreeTableSelectionKeys } from '@/components/common/treeTable';
import { Button } from '@/components/common/button';
import type { TreeNode } from '../../types';
import { convertToTreeTableNodes, getMenuTreeColumns } from './utils/index';

interface Props {
  treeNodes: TreeNode[];
  loading: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'node-select', node: TreeNode): void;
  (e: 'node-unselect'): void;
}>();

const toast = useToast();
const selectionKeys = ref<TreeTableSelectionKeys>({});
const expandedKeys = ref<Record<string, boolean>>({});

const columns = computed(() => getMenuTreeColumns());

const treeTableNodes = computed(() =>
  convertToTreeTableNodes(props.treeNodes)
);

function collectExpandedKeys(nodes: PrimeTreeNode[]): Record<string, boolean> {
  const out: Record<string, boolean> = {};
  const walk = (list: PrimeTreeNode[]) => {
    list.forEach((n) => {
      if (n.children?.length) {
        out[String(n.key)] = true;
        walk(n.children);
      }
    });
  };
  walk(nodes);
  return out;
}

watch(
  treeTableNodes,
  (nodes) => {
    expandedKeys.value = collectExpandedKeys(nodes);
  },
  { immediate: true }
);

const handleNodeSelect = (node: PrimeTreeNode) => {
  const mapped: TreeNode = {
    key: String(node.key ?? ''),
    label: String(node.data?.menuNm ?? node.data?.nodeName ?? ''),
    data: node.data as Record<string, any> | undefined,
    icon: node.data?.icon,
    leaf: node.data?.isLeaf ?? false,
  };
  emit('node-select', mapped);
};

const handleNodeUnselect = () => {
  emit('node-unselect');
};

const collapseAll = () => {
  expandedKeys.value = {};
};

const onSaveClick = () => {
  toast.add({
    severity: 'info',
    summary: '템플릿',
    detail: '저장 API를 연결하세요.',
    life: 2500,
  });
};

defineExpose({ selectionKeys, expandedKeys });
</script>

<style scoped lang="scss" src="./TypeCTree.scss"></style>
