<template>
  <div class="type-c-screen">
    <div class="type-c-header">
      <ContentHeader menuId="SCREEN_ID" />
      <TypeCSearchForm @search="handleSearch" />
    </div>

    <div class="type-c-body">
      <!-- 트리 패널 -->
      <div class="tree-panel">
        <TypeCTree
          :treeNodes="treeNodes"
          :loading="false"
          @node-select="handleNodeSelect"
          @node-unselect="handleNodeUnselect"
        />
      </div>

      <!-- 구분선 -->
      <div class="gutter" />

      <!-- 데이터 패널 -->
      <div class="data-panel">
        <TypeCDataTable
          :fetchedMainData="fetchedMainData"
          :loading="false"
          @row-dblclick="handleRowDblClick"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, provide } from 'vue';
import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue';
import TypeCSearchForm from './components/TypeCSearchForm/TypeCSearchForm.vue';
import TypeCTree from './components/TypeCTree/TypeCTree.vue';
import TypeCDataTable from './components/TypeCDataTable/TypeCDataTable.vue';
import type { MainData, SearchParams, TreeNode } from './types';
import { getTypeCDemoListRows, getTypeCDemoMenuTree } from './utils/treeMapping';

const searchParams    = ref<SearchParams>({ status: null, keyword: '' });
const treeNodes       = ref<TreeNode[]>(getTypeCDemoMenuTree());
const fetchedMainData = ref<MainData[]>(getTypeCDemoListRows());
const selectedNode    = ref<TreeNode | null>(null);

provide('searchParams', searchParams);
provide('selectedNode', selectedNode);

const handleSearch       = () => {};
const handleNodeSelect   = (node: TreeNode) => { selectedNode.value = node; };
const handleNodeUnselect = () => { selectedNode.value = null; };
const handleRowDblClick  = (row: MainData) => { console.log('dblclick', row); };
</script>

<style scoped lang="scss" src="./TypeCScreen.scss"></style>
