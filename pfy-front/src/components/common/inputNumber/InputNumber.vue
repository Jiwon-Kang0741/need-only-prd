<template>
  <PrimeInputNumber
    v-bind="$attrs"
    v-model="model"
    :placeholder="placeholder"
    :invalid="invalid"
    :disabled="disabled"
    :min="min"
    :max="max"
    :mode="mode"
  />
</template>

<script lang="ts" setup>
import PrimeInputNumber from 'primevue/inputnumber';

const model = defineModel<number | null>();

defineProps<{
  placeholder?: string;
  invalid?: boolean;
  disabled?: boolean;
  min?: number;
  max?: number;
  mode?: string;
}>();
</script>
