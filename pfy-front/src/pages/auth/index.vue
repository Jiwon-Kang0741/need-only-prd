<template>
  <div class="auth-layout">
    <RouterView />
  </div>
</template>

<script lang="ts" setup>
</script>

<style scoped>
.auth-layout {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--surface-ground, #f8fafc);
}
</style>
