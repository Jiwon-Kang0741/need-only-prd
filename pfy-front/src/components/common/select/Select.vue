<template>
  <PrimeSelect
    v-bind="$attrs"
    v-model="model"
    :options="options"
    :optionLabel="optionLabel"
    :optionValue="optionValue"
    :placeholder="placeholder"
    :showClear="showClear"
    :invalid="invalid"
    :disabled="disabled"
    :loading="loading"
  />
</template>

<script lang="ts" setup>
import PrimeSelect from 'primevue/select';

const model = defineModel<any>();

defineProps<{
  options?: any[];
  optionLabel?: string;
  optionValue?: string;
  placeholder?: string;
  showClear?: boolean;
  invalid?: boolean;
  disabled?: boolean;
  loading?: boolean;
}>();
</script>
