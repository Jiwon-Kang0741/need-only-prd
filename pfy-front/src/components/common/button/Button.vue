<template>
  <PrimeButton class="button-root" v-bind="$attrs" :label="label" :icon="icon" :variant="variant" :severity="severity" :loading="loading" :disabled="disabled">
    <slot />
  </PrimeButton>
</template>

<script lang="ts" setup>
import PrimeButton from 'primevue/button';

defineProps<{
  label?: string;
  icon?: string;
  variant?: string;
  severity?: string;
  loading?: boolean;
  disabled?: boolean;
}>();
</script>

<style lang="scss" src="./button.scss"></style>
