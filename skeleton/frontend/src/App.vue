<template>
  <div id="app">
    <Toast />
    <ConfirmDialog />
    <router-view />
  </div>
</template>

<script setup lang="ts">
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
</script>

<style>
:root {
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --bg-1: #ffffff;
  --bg-2: #f8f9fa;
  --bg-3: #e9ecef;
  --text-1: #212529;
  --text-2: #495057;
  --text-3: #868e96;
  --border-1: #dee2e6;
  --border-2: #e9ecef;
  --border-radius-sm: 4px;
  --border-radius-md: 8px;
  --border-radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
  --primary: #4263eb;
  --primary-hover: #3b5bdb;
  --danger: #e03131;
  --success: #2f9e44;
  --warning: #f08c00;
}
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: var(--text-1); background: var(--bg-2); }
#app { min-height: 100vh; }
.main-content-container { padding: var(--spacing-lg); max-width: 1400px; margin: 0 auto; }
.cell-input { width: 100%; border: none; background: transparent; padding: 4px 8px; }
.cell-input:focus { outline: 2px solid var(--primary); border-radius: var(--border-radius-sm); }
</style>
