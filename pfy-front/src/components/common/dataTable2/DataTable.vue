<template>
  <PrimeDataTable v-bind="$attrs">
    <slot />
  </PrimeDataTable>
</template>

<script lang="ts" setup>
import PrimeDataTable from 'primevue/datatable';
</script>

<style lang="scss" src="./dataTable.scss"></style>
