<template>
  <PrimeSplitter v-bind="$attrs" :layout="layout" :gutterSize="gutterSize">
    <slot />
  </PrimeSplitter>
</template>

<script lang="ts" setup>
import PrimeSplitter from 'primevue/splitter';

withDefaults(defineProps<{
  layout?: 'horizontal' | 'vertical';
  gutterSize?: number;
}>(), {
  layout: 'horizontal',
  gutterSize: 4,
});
</script>
