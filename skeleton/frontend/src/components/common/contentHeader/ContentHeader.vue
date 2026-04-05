<template>
  <div class="content-header">
    <div class="content-header-left">
      <button v-if="showBack" class="back-btn" @click="$router.back()">
        <i class="pi pi-arrow-left" />
      </button>
      <div>
        <h2 class="content-header-title">{{ screenName || menuId || screenId || 'Untitled' }}</h2>
        <span v-if="screenId" class="content-header-id">{{ screenId }}</span>
      </div>
    </div>
    <div class="content-header-right">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  screenId?: string
  screenName?: string
  menuId?: string
  showBack?: boolean
}>()
</script>

<style scoped>
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--bg-1, #fff);
  border-radius: var(--border-radius-lg, 12px);
  border: 1px solid var(--border-1, #dee2e6);
}
.content-header-left { display: flex; align-items: center; gap: 12px; }
.back-btn {
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; border-radius: 8px;
  border: 1px solid var(--border-1, #dee2e6); background: transparent;
  cursor: pointer; color: var(--text-2, #495057);
}
.back-btn:hover { background: var(--bg-3, #e9ecef); }
.content-header-title { margin: 0; font-size: 18px; font-weight: 600; color: var(--text-1, #212529); }
.content-header-id { font-size: 11px; color: var(--text-3, #868e96); font-family: monospace; }
.content-header-right { display: flex; gap: 8px; }
</style>
