<template>
  <div class="search-form-container">
    <SearchForm ref="searchFormRef">
      <SearchFormRow>
        <!-- 조회기간 -->
        <SearchFormField v-slot="{ props, invalid }" name="searchDt">
          <SearchFormLabel>조회기간</SearchFormLabel>
          <SearchFormContent>
            <RangeDatePicker v-bind="props" :invalid="invalid" placeholder="기간 선택" />
          </SearchFormContent>
        </SearchFormField>

        <!-- 상태 -->
        <SearchFormField v-slot="{ props, invalid }" name="status">
          <SearchFormLabel>상태</SearchFormLabel>
          <SearchFormContent>
            <Select
              v-bind="props"
              :invalid="invalid"
              :options="statusOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="전체"
              :showClear="true"
            />
          </SearchFormContent>
        </SearchFormField>

        <!-- 키워드 -->
        <SearchFormField v-slot="{ props, invalid }" name="keyword">
          <SearchFormLabel>검색어</SearchFormLabel>
          <SearchFormContent>
            <InputText v-bind="props" :invalid="invalid" placeholder="검색어를 입력하세요" />
          </SearchFormContent>
        </SearchFormField>
      </SearchFormRow>

      <template #buttons>
        <Button label="초기화" variant="outlined" icon="pi pi-refresh" @click="handleReset" />
        <Button label="조회" icon="pi pi-search" @click="handleSearch" />
      </template>
    </SearchForm>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, inject, watch, onMounted } from 'vue';
import type { Ref } from 'vue';
import {
  SearchForm,
  SearchFormContent,
  SearchFormField,
  SearchFormRow,
} from '@/components/common/searchForm';
import SearchFormLabel from '@/components/common/searchForm/SearchFormLabel.vue';
import { Button } from '@/components/common/button';
import { RangeDatePicker } from '@/components/common/datePicker';
import Select from '@/components/common/select/Select.vue';
import InputText from '@/components/common/inputText/InputText.vue';
import { useCommonCodeStore } from '@/stores/commonCodeStore';
import type { SearchParams } from '../../index.vue';

const emit = defineEmits<{ (e: 'search'): void }>();

const searchParams = inject<Ref<SearchParams>>('searchParams')!;
const searchFormRef = ref();
const commonCodeStore = useCommonCodeStore();

onMounted(async () => {
  await commonCodeStore.loadMulti([
    { QueryId: 'MNPS010Query.StatComboIn', customParam: 'BUSN_SC_IN=A1 PROG_ID=SCREEN_ID' },
  ]);
});

const statusOptions = computed(() =>
  commonCodeStore.options('MNPS010Query.StatComboIn', true, '전체', '')
);

watch(
  () => searchParams.value?.status,
  (newVal) => {
    if (newVal !== undefined && searchFormRef.value?.form) {
      searchFormRef.value.form.setFieldValue('status', newVal ?? '');
    }
  }
);

const handleSearch = () => emit('search');

const handleReset = () => {
  searchFormRef.value?.form?.reset();
  searchParams.value = { status: null, keyword: '' };
};

defineExpose({ searchFormRef });
</script>

<style scoped lang="scss" src="./TypeDSearchForm.scss"></style>
