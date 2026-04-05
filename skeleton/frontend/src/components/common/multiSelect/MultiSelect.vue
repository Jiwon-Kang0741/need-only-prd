<template>
  <MultiSelect v-bind="$attrs" :modelValue="modelValue" :options="options" @update:modelValue="$emit('update:modelValue', $event)" />
</template>

<script setup lang="ts">
import MultiSelect from 'primevue/multiselect'
defineProps<{ modelValue?: unknown[]; options?: unknown[] }>()
defineEmits<{ 'update:modelValue': [value: unknown[]] }>()
</script>
