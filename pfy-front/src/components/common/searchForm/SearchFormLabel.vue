<template>
  <label class="search-form-label">
    <slot />
  </label>
</template>

<script lang="ts" setup>
</script>

<style scoped>
.search-form-label {
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-color-secondary, #64748b);
  min-width: 80px;
}
</style>
