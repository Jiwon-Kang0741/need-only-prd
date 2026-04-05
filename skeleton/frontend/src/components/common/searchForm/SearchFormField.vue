<template>
  <div class="search-form-field">
    <slot :props="fieldProps" :invalid="false" />
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'

const props = defineProps<{ name?: string }>()

const formValues = inject<Record<string, unknown>>('searchFormValues', {})
const formUpdate = inject<(name: string, value: unknown) => void>('searchFormUpdate', () => {})

const fieldProps = computed(() => ({
  modelValue: props.name ? formValues[props.name] : undefined,
  'onUpdate:modelValue': (v: unknown) => {
    if (props.name) formUpdate(props.name, v)
  },
}))
</script>

<style scoped>
.search-form-field { display: flex; align-items: center; gap: 8px; }
</style>
