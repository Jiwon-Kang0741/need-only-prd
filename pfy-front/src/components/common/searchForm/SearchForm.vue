<template>
  <div class="search-form-container">
    <div class="search-form">
      <div class="field-group">
        <slot />
      </div>
      <div class="button-group">
        <slot name="buttons" />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue';

const formValues = ref<Record<string, any>>({});
const invalidFields = ref<Set<string>>(new Set());

const form = {
  setFieldValue(name: string, value: any) {
    formValues.value[name] = value;
  },
  getFieldValue(name: string) {
    return formValues.value[name];
  },
  reset() {
    formValues.value = {};
    invalidFields.value.clear();
  },
};

defineExpose({ form });
</script>

<style scoped lang="scss" src="./searchForm.scss"></style>
