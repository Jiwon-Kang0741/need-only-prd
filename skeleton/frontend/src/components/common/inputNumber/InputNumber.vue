<template>
  <InputNumber v-bind="$attrs" :modelValue="modelValue" @update:modelValue="$emit('update:modelValue', $event)" />
</template>

<script setup lang="ts">
import InputNumber from 'primevue/inputnumber'
defineProps<{ modelValue?: number }>()
defineEmits<{ 'update:modelValue': [value: number] }>()
</script>
