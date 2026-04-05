<template>
  <div class="search-form">
    <div class="search-form-body">
      <!-- Pattern A: config-based auto rendering -->
      <template v-if="config && config.groups">
        <div v-for="group in config.groups" :key="group.label" class="search-form-group">
          <div v-if="group.label" class="search-form-group-label">{{ group.label }}</div>
          <div class="search-form-fields">
            <div v-for="field in group.fields" :key="field.name" class="search-form-field-item">
              <label class="search-form-label">{{ field.label }}</label>
              <div class="search-form-input">
                <InputText
                  v-if="!field.component || field.component === 'InputText'"
                  :modelValue="formValues[field.name] || ''"
                  :placeholder="field.props?.placeholder || ''"
                  @update:modelValue="(v) => updateField(field.name, v)"
                />
                <Dropdown
                  v-else-if="field.component === 'Dropdown' || field.component === 'Select'"
                  :modelValue="formValues[field.name]"
                  :options="field.props?.options || []"
                  :optionLabel="field.props?.optionLabel || 'label'"
                  :optionValue="field.props?.optionValue || 'value'"
                  :placeholder="field.props?.placeholder || '선택'"
                  @update:modelValue="(v) => updateField(field.name, v)"
                />
                <Calendar
                  v-else-if="field.component === 'Calendar' || field.component === 'DatePicker'"
                  :modelValue="formValues[field.name]"
                  dateFormat="yy-mm-dd"
                  @update:modelValue="(v) => updateField(field.name, v)"
                />
                <InputText
                  v-else
                  :modelValue="formValues[field.name] || ''"
                  :placeholder="field.props?.placeholder || ''"
                  @update:modelValue="(v) => updateField(field.name, v)"
                />
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Pattern B: slot-based -->
      <div v-else class="search-form-fields">
        <slot />
      </div>
    </div>

    <div class="search-form-actions">
      <slot name="actions">
        <slot name="additionalButtons" />
        <Button label="조회" icon="pi pi-search" @click="handleSearch" />
        <Button label="초기화" severity="secondary" @click="handleReset" />
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, provide, ref } from 'vue'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Calendar from 'primevue/calendar'
import Button from 'primevue/button'

interface FieldConfig {
  name: string
  label: string
  component?: string
  props?: Record<string, unknown>
}

interface GroupConfig {
  label?: string
  fields: FieldConfig[]
}

interface SearchFormConfig {
  groups: GroupConfig[]
}

const props = defineProps<{
  config?: SearchFormConfig
  modelValue?: Record<string, unknown>
}>()

const emit = defineEmits<{
  search: []
  reset: []
  'update:modelValue': [value: Record<string, unknown>]
}>()

const formValues = reactive<Record<string, unknown>>(props.modelValue || {})

function updateField(name: string, value: unknown) {
  formValues[name] = value
  emit('update:modelValue', { ...formValues })
}

function setFieldValue(name: string, value: unknown) {
  formValues[name] = value
}

function getFieldValue(name: string) {
  return formValues[name]
}

function handleSearch() {
  emit('search')
}

function handleReset() {
  Object.keys(formValues).forEach(k => { formValues[k] = '' })
  emit('reset')
}

// Provide form to children (for slot-based pattern)
provide('searchFormValues', formValues)
provide('searchFormUpdate', updateField)

// Expose form API for external access (searchFormRef.value.form.setFieldValue)
const form = { setFieldValue, getFieldValue, values: formValues }
defineExpose({ form, setFieldValue, getFieldValue })
</script>

<style scoped>
.search-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-1, #fff);
  border-radius: var(--border-radius-lg, 12px);
  border: 1px solid var(--border-1, #dee2e6);
}
.search-form-body { flex: 1; }
.search-form-group-label { font-size: 12px; font-weight: 600; color: var(--text-3, #868e96); margin-bottom: 8px; text-transform: uppercase; }
.search-form-fields { display: flex; flex-wrap: wrap; gap: 12px; }
.search-form-field-item { display: flex; align-items: center; gap: 8px; }
.search-form-label { font-size: 13px; font-weight: 500; color: var(--text-2, #495057); white-space: nowrap; min-width: 70px; }
.search-form-input { min-width: 160px; }
.search-form-actions { display: flex; gap: 8px; justify-content: flex-end; padding-top: 8px; border-top: 1px solid var(--border-2, #e9ecef); }
</style>
