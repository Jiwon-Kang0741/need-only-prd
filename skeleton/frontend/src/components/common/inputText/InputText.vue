<template>
  <InputText v-bind="$attrs" :modelValue="modelValue" @update:modelValue="$emit('update:modelValue', $event)" />
</template>

<script setup lang="ts">
import InputText from 'primevue/inputtext'
defineProps<{ modelValue?: string; invalid?: boolean; placeholder?: string }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
