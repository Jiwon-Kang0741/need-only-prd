<template>
  <!--
  ┌─────────────────────────────────────────────────────────────────────┐
  │  StandardEditTemplate — Form Layout                                 │
  │                                                                     │
  │  Layout 구조                                                         │
  │  ──────────────────────────────────────────────────────────────     │
  │  [ breadcrumb?  ]                                                   │
  │  [ title        ]                                                   │
  │  [ description? ]  보조 설명 문구 (선택)                             │
  │  ─────────────────────────────────────────────────────             │
  │  [ default      ]  입력 폼 섹션 영역 (스크롤, flex:1)               │
  │  ─────────────────────────────────────────────────────             │
  │  [ footer-left? ] [ footer-right? ]  하단 버튼 행                  │
  │                                                                     │
  │  Named Slots                                                        │
  │  ──────────────────────────────────────────────────────────────     │
  │  #title          화면 제목                                           │
  │  #breadcrumb     메뉴 경로 (선택)                                    │
  │  #description    화면 설명 문구 (선택)                               │
  │  #default        입력 폼 필드 영역 (기본 슬롯)                       │
  │  #footer-left    하단 좌측 버튼 영역 (선택)                          │
  │  #footer-right   하단 우측 버튼 영역 (선택)                          │
  └─────────────────────────────────────────────────────────────────────┘
  -->
  <div class="std-edit">

    <!-- ── 상단 헤더 블록 ─────────────────────────────────────────────── -->
    <div class="std-edit__head">

      <!-- breadcrumb -->
      <div v-if="$slots.breadcrumb" class="std-edit__breadcrumb">
        <slot name="breadcrumb">
          <!--
            예시:
            <Breadcrumb :items="[{label:'홈'},{label:'업무관리'},{label:'신규 등록'}]" />
          -->
        </slot>
      </div>

      <!-- title -->
      <div class="std-edit__title">
        <slot name="title">
          <!--
            예시 — 독립 페이지:
            <h2>신규 등록</h2>
            또는
            <ContentHeader :title="isEdit ? '수정' : '신규 등록'" />
          -->
        </slot>
      </div>

      <!-- description (보조 설명) -->
      <div v-if="$slots.description" class="std-edit__description">
        <slot name="description">
          <!--
            예시:
            <p>* 표시된 항목은 필수 입력 항목입니다.</p>
          -->
        </slot>
      </div>
    </div>

    <!-- ── 로딩 오버레이 ─────────────────────────────────────────────── -->
    <div v-if="loading" class="std-edit__loading" aria-live="polite">
      <i class="pi pi-spin pi-spinner" aria-hidden="true" />
      <span>불러오는 중...</span>
    </div>

    <!-- ── 폼 필드 영역 (default slot, 스크롤) ──────────────────────── -->
    <div v-else class="std-edit__body">
      <slot>
        <!--
          예시 — form-section / form-row 유틸 클래스 활용:
          <section class="form-section">
            <h3 class="form-section__title">기본 정보</h3>

            <div class="form-row">
              <label class="form-label required">신고 유형</label>
              <div class="form-control">
                <Select v-model="form.reportType" :options="reportTypeOptions"
                  optionLabel="label" optionValue="value" placeholder="선택" />
              </div>
            </div>

            <div class="form-row">
              <label class="form-label required">신고 제목</label>
              <div class="form-control">
                <InputText v-model="form.title" placeholder="제목을 입력하세요" />
              </div>
            </div>

            <div class="form-row form-row--full">
              <label class="form-label">신고 내용</label>
              <div class="form-control">
                <Textarea v-model="form.content" rows="6" autoResize />
              </div>
            </div>
          </section>

          <section class="form-section">
            <h3 class="form-section__title">첨부파일</h3>
            <AttachmentList v-model:files="form.attachments" editable />
          </section>
        -->
      </slot>
    </div>

    <!-- ── 하단 버튼 행 ──────────────────────────────────────────────── -->
    <div
      v-if="$slots['footer-left'] || $slots['footer-right']"
      class="std-edit__footer"
    >
      <div v-if="$slots['footer-left']" class="std-edit__footer-left">
        <slot name="footer-left">
          <!--
            예시 (좌측):
            <Button label="임시 저장" severity="secondary" variant="outlined" @click="onDraft" />
          -->
        </slot>
      </div>
      <div v-if="$slots['footer-right']" class="std-edit__footer-right">
        <slot name="footer-right">
          <!--
            예시 (우측):
            <Button label="저장" icon="pi pi-check" :loading="saving" @click="onSave" />
            <Button label="취소" severity="secondary" variant="outlined" @click="onCancel" />
          -->
        </slot>
      </div>
    </div>

  </div>
</template>

<script lang="ts" setup>
withDefaults(defineProps<{
  /** 데이터 초기 로딩 중 (수정 모드에서 기존 데이터 fetch 시) */
  loading?: boolean;
  /** 저장 API 호출 중 (footer-right 의 저장 버튼 :loading prop 으로 바인딩) */
  saving?: boolean;
}>(), {
  loading: false,
  saving: false,
});
</script>

<style scoped lang="scss">
.std-edit {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--bg-1);
  overflow: hidden;
  box-sizing: border-box;

  /* ── 상단 헤더 블록 ── */
  &__head {
    flex-shrink: 0;
    padding: 20px 24px 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  /* breadcrumb */
  &__breadcrumb {
    margin-bottom: 2px;
  }

  /* title */
  &__title {
    min-height: 36px;
    display: flex;
    align-items: center;
  }

  /* description */
  &__description {
    font-size: 13px;
    color: var(--txt-color-3);
    padding-bottom: 8px;
    border-bottom: 1px solid var(--divider-1);
    margin-top: 4px;
  }

  /* ── 로딩 ── */
  &__loading {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--txt-color-3);

    .pi {
      font-size: 28px;
    }

    span {
      font-size: 13px;
    }
  }

  /* ── 폼 영역 (default slot) — 스크롤, 남은 공간 전부 ── */
  &__body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 16px 24px 20px;
  }

  /* ── 하단 버튼 행 ── */
  &__footer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
    border-top: 1px solid var(--divider-1);
    background-color: var(--bg-1);
  }

  &__footer-left {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  &__footer-right {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
  }
}

/* ──────────────────────────────────────────────────────────────────────
   #default 슬롯 내부에서 사용하는 form-section / form-row 유틸 클래스
   ────────────────────────────────────────────────────────────────────── */
:deep(.form-section) {
  margin-bottom: 24px;
}

:deep(.form-section__title) {
  font-size: 13px;
  font-weight: 600;
  color: var(--txt-color-2);
  padding: 8px 0;
  margin: 0 0 12px;
  border-bottom: 2px solid var(--divider-2);
}

:deep(.form-row) {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 6px 0;
  font-size: 13px;
}

:deep(.form-row.form-row--full) {
  flex-direction: row;
  align-items: flex-start;

  .form-label {
    padding-top: 6px;
  }

  .form-control {
    flex: 1;
  }
}

:deep(.form-row .form-label) {
  flex-shrink: 0;
  width: 110px;
  font-weight: 500;
  color: var(--txt-color-3);
  text-align: right;
  padding-top: 7px;
}

:deep(.form-row .form-label.required::after) {
  content: ' *';
  color: var(--error-color);
}

:deep(.form-row .form-control) {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

:deep(.form-row .form-error) {
  color: var(--error-color);
  font-size: 12px;
}
</style>
