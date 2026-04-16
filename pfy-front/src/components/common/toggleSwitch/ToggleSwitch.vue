<template>
  <PrimeToggleSwitch v-bind="$attrs" v-model="model" :disabled="disabled" />
</template>

<script lang="ts" setup>
import PrimeToggleSwitch from 'primevue/toggleswitch';

const model = defineModel<boolean>();

defineProps<{
  disabled?: boolean;
}>();
</script>
