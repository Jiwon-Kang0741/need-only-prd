<template>
  <PrimeDatePicker
    v-bind="$attrs"
    v-model="model"
    selectionMode="range"
    :placeholder="placeholder"
    :invalid="invalid"
    :disabled="disabled"
    :showIcon="true"
    dateFormat="yy-mm-dd"
  />
</template>

<script lang="ts" setup>
import PrimeDatePicker from 'primevue/datepicker';

const model = defineModel<any>();

defineProps<{
  placeholder?: string;
  invalid?: boolean;
  disabled?: boolean;
}>();
</script>
