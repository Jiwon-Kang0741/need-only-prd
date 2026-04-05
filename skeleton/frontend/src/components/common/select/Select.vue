<template>
  <Dropdown v-bind="$attrs" :modelValue="modelValue" :options="options" :optionLabel="optionLabel" :optionValue="optionValue" @update:modelValue="$emit('update:modelValue', $event)" />
</template>

<script setup lang="ts">
import Dropdown from 'primevue/dropdown'
defineProps<{ modelValue?: unknown; options?: unknown[]; optionLabel?: string; optionValue?: string }>()
defineEmits<{ 'update:modelValue': [value: unknown] }>()
</script>
