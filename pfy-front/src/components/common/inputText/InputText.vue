<template>
  <PrimeInputText
    v-bind="$attrs"
    v-model="model"
    :placeholder="placeholder"
    :invalid="invalid"
    :disabled="disabled"
  />
</template>

<script lang="ts" setup>
import PrimeInputText from 'primevue/inputtext';

const model = defineModel<string>();

defineProps<{
  placeholder?: string;
  invalid?: boolean;
  disabled?: boolean;
}>();
</script>
