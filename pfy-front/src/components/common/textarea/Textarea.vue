<template>
  <PrimeTextarea
    v-bind="$attrs"
    v-model="model"
    :placeholder="placeholder"
    :invalid="invalid"
    :disabled="disabled"
    :rows="rows"
    :autoResize="autoResize"
  />
</template>

<script lang="ts" setup>
import PrimeTextarea from 'primevue/textarea';

const model = defineModel<string>();

defineProps<{
  placeholder?: string;
  invalid?: boolean;
  disabled?: boolean;
  rows?: number;
  autoResize?: boolean;
}>();
</script>
