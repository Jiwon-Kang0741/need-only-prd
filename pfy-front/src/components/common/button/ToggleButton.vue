<template>
  <PrimeToggleButton v-bind="$attrs" v-model="model" :onLabel="onLabel" :offLabel="offLabel" />
</template>

<script lang="ts" setup>
import PrimeToggleButton from 'primevue/togglebutton';

const model = defineModel<boolean>();

defineProps<{
  onLabel?: string;
  offLabel?: string;
}>();
</script>
