<template>
  <div class="input-form-container">
    <!-- 섹션: 기본 정보 -->
    <section class="form-section">
      <h3 class="section-title">기본 정보</h3>
      <div class="form-grid">

        <!-- 항목번호 (수정 모드 시 읽기 전용) -->
        <div class="field">
          <label class="field-label required">항목번호</label>
          <InputText
            v-model="localForm.itemNo"
            :disabled="isEditMode"
            placeholder="항목번호를 입력하세요"
            :class="{ 'p-invalid': errors.itemNo }"
          />
          <small v-if="errors.itemNo" class="p-error">{{ errors.itemNo }}</small>
        </div>

        <!-- 항목명 -->
        <div class="field">
          <label class="field-label required">항목명</label>
          <InputText
            v-model="localForm.itemNm"
            placeholder="항목명을 입력하세요"
            :class="{ 'p-invalid': errors.itemNm }"
          />
          <small v-if="errors.itemNm" class="p-error">{{ errors.itemNm }}</small>
        </div>

        <!-- 수량 -->
        <div class="field">
          <label class="field-label">수량</label>
          <InputNumber
            v-model="localForm.qty"
            :showButtons="true"
            :min="0"
            buttonLayout="horizontal"
          />
        </div>

        <!-- 상태 -->
        <div class="field">
          <label class="field-label required">상태</label>
          <Select
            v-model="localForm.status"
            :options="statusOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="상태를 선택하세요"
            :class="{ 'p-invalid': errors.status }"
          />
          <small v-if="errors.status" class="p-error">{{ errors.status }}</small>
        </div>
      </div>
    </section>

    <!-- 섹션: 기간 정보 -->
    <section class="form-section">
      <h3 class="section-title">기간 정보</h3>
      <div class="form-grid">

        <!-- 시작일 -->
        <div class="field">
          <label class="field-label">시작일</label>
          <SingleDatePicker
            v-model="localForm.startDt"
            placeholder="시작일 선택"
          />
        </div>

        <!-- 종료일 -->
        <div class="field">
          <label class="field-label">종료일</label>
          <SingleDatePicker
            v-model="localForm.endDt"
            placeholder="종료일 선택"
            :minDate="localForm.startDt ?? undefined"
          />
        </div>
      </div>
    </section>

    <!-- 섹션: 추가 정보 -->
    <section class="form-section">
      <h3 class="section-title">추가 정보</h3>
      <div class="form-grid">

        <!-- 승인 여부 -->
        <div class="field field--inline">
          <label class="field-label">승인 여부</label>
          <ToggleSwitch v-model="localForm.isApproved" />
        </div>

        <!-- 담당자 (예시: 라디오) -->
        <div class="field">
          <label class="field-label">구분</label>
          <div class="radio-group">
            <label v-for="opt in typeOptions" :key="opt.value" class="radio-label">
              <RadioButton
                v-model="localForm.type"
                :value="opt.value"
                name="type"
              />
              {{ opt.label }}
            </label>
          </div>
        </div>

        <!-- 비고 -->
        <div class="field field--full">
          <label class="field-label">비고</label>
          <Textarea
            v-model="localForm.remark"
            rows="4"
            :autoResize="true"
            placeholder="비고를 입력하세요"
          />
        </div>
      </div>
    </section>

    <!-- 하단 버튼 영역 -->
    <div class="form-actions">
      <Button label="취소" variant="outlined" severity="secondary" icon="pi pi-times" @click="handleCancel" />
      <Button label="초기화" variant="outlined" icon="pi pi-refresh" @click="handleReset" />
      <Button
        :label="isEditMode ? '수정' : '등록'"
        :icon="isEditMode ? 'pi pi-pencil' : 'pi pi-check'"
        :loading="loading"
        @click="handleSave"
      />
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch, computed, onMounted } from 'vue';
import { Button } from '@/components/common/button';
import InputText from '@/components/common/inputText/InputText.vue';
import InputNumber from '@/components/common/inputNumber/InputNumber.vue';
import Select from '@/components/common/select/Select.vue';
import { SingleDatePicker } from '@/components/common/datePicker';
import RadioButton from '@/components/common/radioButton/RadioButton.vue';
import ToggleSwitch from '@/components/common/toggleSwitch/ToggleSwitch.vue';
import Textarea from '@/components/common/textarea/Textarea.vue';
import { useCommonCodeStore } from '@/stores/commonCodeStore';
import type { FormData } from '../../index.vue';

// ─── Props ────────────────────────────────────────────────────────────────────
interface Props {
  formData: FormData;
  isEditMode: boolean;
  loading: boolean;
}

const props = defineProps<Props>();

// ─── Emits ───────────────────────────────────────────────────────────────────
const emit = defineEmits<{
  (e: 'save', data: FormData): void;
  (e: 'cancel'): void;
  (e: 'reset'): void;
}>();

// ─── 로컬 폼 상태 (props 복사본으로 독립 관리) ─────────────────────────────────
const localForm = ref<FormData>({ ...props.formData });

watch(
  () => props.formData,
  (newVal) => { localForm.value = { ...newVal }; },
  { deep: true }
);

// ─── 유효성 에러 ──────────────────────────────────────────────────────────────
const errors = ref<Record<string, string>>({});

// ─── 공통코드 ─────────────────────────────────────────────────────────────────
const commonCodeStore = useCommonCodeStore();

onMounted(async () => {
  await commonCodeStore.loadMulti([
    { QueryId: 'MNPS010Query.StatComboIn', customParam: 'BUSN_SC_IN=A1 PROG_ID=SCREEN_ID' },
  ]);
});

const statusOptions = computed(() =>
  commonCodeStore.options('MNPS010Query.StatComboIn', false)
);

// NOTE: 실제 데이터에 맞게 교체하세요
const typeOptions = [
  { label: '유형 A', value: 'A' },
  { label: '유형 B', value: 'B' },
  { label: '유형 C', value: 'C' },
];

// ─── 유효성 검사 ──────────────────────────────────────────────────────────────
const validate = (): boolean => {
  errors.value = {};

  if (!localForm.value.itemNo?.trim()) {
    errors.value.itemNo = '항목번호는 필수입니다.';
  }
  if (!localForm.value.itemNm?.trim()) {
    errors.value.itemNm = '항목명은 필수입니다.';
  }
  if (!localForm.value.status) {
    errors.value.status = '상태를 선택해 주세요.';
  }

  return Object.keys(errors.value).length === 0;
};

// ─── Handlers ─────────────────────────────────────────────────────────────────
const handleSave = () => {
  if (!validate()) return;
  emit('save', { ...localForm.value });
};

const handleCancel = () => {
  emit('cancel');
};

const handleReset = () => {
  errors.value = {};
  emit('reset');
};
</script>

<style scoped lang="scss" src="./TypeBInputForm.scss"></style>
