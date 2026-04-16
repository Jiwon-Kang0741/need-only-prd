<template>
  <PrimePaginator
    class="paginator-root"
    v-bind="$attrs"
    :rows="rows"
    :totalRecords="totalRecords"
    :rowsPerPageOptions="rowsPerPageOptions"
  />
</template>

<script lang="ts" setup>
import PrimePaginator from 'primevue/paginator';

defineProps<{
  rows?: number;
  totalRecords?: number;
  rowsPerPageOptions?: number[];
}>();
</script>

<style lang="scss" src="./paginator.scss"></style>
