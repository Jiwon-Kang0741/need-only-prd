<template>
  <PrimeRadioButton v-bind="$attrs" v-model="model" :value="value" :inputId="inputId" :disabled="disabled" />
</template>

<script lang="ts" setup>
import PrimeRadioButton from 'primevue/radiobutton';

const model = defineModel<any>();

defineProps<{
  value?: any;
  inputId?: string;
  disabled?: boolean;
}>();
</script>
