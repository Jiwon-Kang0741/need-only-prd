<template>
  <div class="content-header">
    <div class="header-main">
      <h2 class="header-title">{{ title || menuId }}</h2>
    </div>
    <div class="header-right">
      <slot name="right" />
    </div>
  </div>
</template>

<script lang="ts" setup>
defineProps<{
  menuId?: string;
  title?: string;
}>();
</script>

<style scoped lang="scss" src="./contentHeader.scss"></style>
