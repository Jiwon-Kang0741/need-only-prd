<template>
  <PrimeSplitterPanel v-bind="$attrs" :size="size" :minSize="minSize">
    <slot />
  </PrimeSplitterPanel>
</template>

<script lang="ts" setup>
import PrimeSplitterPanel from 'primevue/splitterpanel';

withDefaults(defineProps<{
  size?: number;
  minSize?: number;
}>(), {
  size: 50,
  minSize: 10,
});
</script>
