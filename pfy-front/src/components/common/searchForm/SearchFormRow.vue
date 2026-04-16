<template>
  <div class="search-form-row">
    <slot />
  </div>
</template>

<script lang="ts" setup>
</script>

<style scoped>
.search-form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  width: 100%;
}
</style>
