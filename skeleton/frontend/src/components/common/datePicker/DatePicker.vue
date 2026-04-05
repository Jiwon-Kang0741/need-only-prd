<template>
  <Calendar v-bind="$attrs" :modelValue="modelValue" dateFormat="yy-mm-dd" @update:modelValue="$emit('update:modelValue', $event)" />
</template>

<script setup lang="ts">
import Calendar from 'primevue/calendar'
defineProps<{ modelValue?: Date | string }>()
defineEmits<{ 'update:modelValue': [value: unknown] }>()
</script>
