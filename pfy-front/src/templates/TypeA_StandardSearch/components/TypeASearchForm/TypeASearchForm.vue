<template>
  <div class="search-form-container">
    <SearchForm ref="searchFormRef">
      <SearchFormRow>
        <!-- 조회기간 구분 -->
        <SearchFormField v-slot="{ props, invalid }" name="searchDtType">
          <SearchFormLabel>조회기간 구분</SearchFormLabel>
          <SearchFormContent>
            <Select
              v-bind="props"
              :invalid="invalid"
              :options="dateTypeOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="선택"
            />
          </SearchFormContent>
        </SearchFormField>

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

// ─── Emits ───────────────────────────────────────────────────────────────────
const emit = defineEmits<{ (e: 'search'): void }>();

// ─── Inject ──────────────────────────────────────────────────────────────────
const searchParams = inject<Ref<SearchParams>>('searchParams')!;

// ─── Refs ────────────────────────────────────────────────────────────────────
const searchFormRef = ref();
const commonCodeStore = useCommonCodeStore();

// ─── 공통코드 로딩 ────────────────────────────────────────────────────────────
onMounted(async () => {
  // NOTE: QueryId를 실제 사용하는 공통코드로 교체하세요
  await commonCodeStore.loadMulti([
    { QueryId: 'MNPS010Query.StatComboIn', customParam: 'BUSN_SC_IN=A1 PROG_ID=SCREEN_ID' },
    { QueryId: 'MNPS010Query.DateCond', customParam: 'BUSN_SC_IN=A1 PROG_ID=SCREEN_ID' },
  ]);
});

// ─── Computed Options ─────────────────────────────────────────────────────────
const statusOptions = computed(() =>
  commonCodeStore.options('MNPS010Query.StatComboIn', true, '전체', '')
);

const dateTypeOptions = computed(() =>
  commonCodeStore.options('MNPS010Query.DateCond', false)
);

// ─── Watch: SearchParams 동기화 ───────────────────────────────────────────────
// SumGrid 또는 외부에서 searchParams.status 변경 시 SelectBox 동기화
watch(
  () => searchParams.value?.status,
  (newVal) => {
    if (newVal !== undefined && searchFormRef.value?.form) {
      searchFormRef.value.form.setFieldValue('status', newVal ?? '');
    }
  }
);

// ─── Handlers ─────────────────────────────────────────────────────────────────
const handleSearch = () => {
  emit('search');
};

const handleReset = () => {
  searchFormRef.value?.form?.reset();
  searchParams.value = {
    status: null,
    keyword: '',
    searchDtType: 'default',
    searchDt: [],
  };
};

// ─── Expose ──────────────────────────────────────────────────────────────────
defineExpose({ searchFormRef });
</script>

<style scoped lang="scss" src="./TypeASearchForm.scss"></style>
