<template>
  <div class="search-form-field">
    <slot :props="fieldProps" :invalid="false" />
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue';

const props = defineProps<{
  name: string;
}>();

const fieldProps = computed(() => ({
  id: props.name,
  name: props.name,
}));
</script>

<style scoped>
.search-form-field {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 200px;
}
</style>
