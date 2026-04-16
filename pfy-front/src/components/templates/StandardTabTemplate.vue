<template>
  <!--
  ┌─────────────────────────────────────────────────────────────────────┐
  │  StandardTabTemplate                                                │
  │  표준 탭 화면 템플릿                                                  │
  │                                                                     │
  │  주요 사용 시나리오                                                   │
  │  ──────────────────────────────────────────────────────────────     │
  │  1) 상세 정보를 여러 탭(기본정보·처리이력·첨부파일 등)으로 분리할 때    │
  │  2) 입력 폼을 탭별로 분리할 때 (기본정보/추가정보/첨부파일)             │
  │  3) StandardListTemplate 의 #right-drawer 안에서 탭형 상세로 사용    │
  │                                                                     │
  │  Layout 구조                                                         │
  │  ──────────────────────────────────────────────────────────────     │
  │  [ header  ]  ContentHeader                                         │
  │  ────────────────────────────────                                   │
  │  [ Tab 헤더 ] Tab1 | Tab2 | Tab3 | ...                              │
  │  ────────────────────────────────                                   │
  │  [ #panel-{tab.key} ]  활성 탭 패널 내용 (스크롤)                    │
  │  ────────────────────────────────                                   │
  │  [ actions ]  하단 버튼 영역 (저장·취소 등)                           │
  │                                                                     │
  │  isEmpty=true 일 때 → [ #empty ] 슬롯 표시                           │
  │                                                                     │
  │  Props                                                              │
  │  ──────────────────────────────────────────────────────────────     │
  │  tabs          TabItem[] — 탭 목록 (key, label, disabled?)           │
  │  modelValue    현재 활성 탭 key (v-model)                            │
  │  loading       데이터 로딩 중                                         │
  │  isEmpty       항목 미선택                                            │
  │                                                                     │
  │  Named Slots                                                        │
  │  ──────────────────────────────────────────────────────────────     │
  │  #header          화면 제목                                          │
  │  #panel-{tab.key} 각 탭 패널 내용 (tabs prop 의 key 와 매핑)          │
  │  #actions         하단 버튼                                          │
  │  #empty           항목 미선택 안내                                    │
  └─────────────────────────────────────────────────────────────────────┘
  -->
  <div class="std-tab" :class="{ 'std-tab--empty-state': isEmpty }">

    <!-- ─────────────────────────────────────────────────────────────── -->
    <!-- 항목 미선택 상태                                                 -->
    <!-- ─────────────────────────────────────────────────────────────── -->
    <template v-if="isEmpty">
      <div class="std-tab__empty">
        <slot name="empty">
          <div class="std-tab__empty-default">
            <i class="pi pi-list" />
            <p>목록에서 항목을 선택하세요.</p>
          </div>
        </slot>
      </div>
    </template>

    <!-- ─────────────────────────────────────────────────────────────── -->
    <!-- 항목 선택됨 → Header / Tabs / Actions                           -->
    <!-- ─────────────────────────────────────────────────────────────── -->
    <template v-else>

      <!-- ① Header -->
      <div v-if="$slots.header" class="std-tab__header">
        <slot name="header">
          <!--
            예시:
            <ContentHeader title="신고 상세" />
          -->
        </slot>
      </div>

      <!-- ② Loading 상태 -->
      <div v-if="loading" class="std-tab__loading">
        <i class="pi pi-spin pi-spinner" />
        <span>불러오는 중...</span>
      </div>

      <!-- ③ Tab 영역 -->
      <div v-else class="std-tab__tabs-wrapper">

        <!-- ── 탭 헤더 바 ────────────────────────────────────────── -->
        <div class="std-tab__tab-bar" role="tablist">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="std-tab__tab-btn"
            :class="{
              'std-tab__tab-btn--active': activeKey === tab.key,
              'std-tab__tab-btn--disabled': tab.disabled,
            }"
            role="tab"
            :aria-selected="activeKey === tab.key"
            :disabled="tab.disabled"
            @click="onTabClick(tab.key)"
          >
            {{ tab.label }}
            <!-- 뱃지 표시 (선택적) -->
            <span v-if="tab.badge != null" class="std-tab__tab-badge">
              {{ tab.badge }}
            </span>
          </button>
        </div>

        <!-- ── 탭 패널 콘텐츠 ────────────────────────────────────── -->
        <div class="std-tab__panels">
          <template v-for="tab in tabs" :key="tab.key">
            <!--
              활성 탭만 렌더링 (keepAlive=true 이면 모두 렌더링 후 hidden)
              슬롯 이름 규칙: panel-{tab.key}
            -->
            <div
              class="std-tab__panel"
              :class="{ 'std-tab__panel--hidden': activeKey !== tab.key }"
              role="tabpanel"
              :aria-hidden="activeKey !== tab.key"
            >
              <slot :name="`panel-${tab.key}`">
                <!--
                  예시 (tabs=[{key:'basic',...},{key:'history',...},{key:'files',...}]):

                  ─── #panel-basic ───────────────────────────────────
                  <template #panel-basic>
                    <div class="form-row">
                      <span class="detail-label">신고 유형</span>
                      <span class="detail-value">{{ item.reportTypeNm }}</span>
                    </div>
                    <div class="form-row">
                      <span class="detail-label">제목</span>
                      <span class="detail-value">{{ item.title }}</span>
                    </div>
                  </template>

                  ─── #panel-history ─────────────────────────────────
                  <template #panel-history>
                    <DataTable :value="historyRows" scrollable scrollHeight="flex">
                      <Column field="actionDt"  header="처리일시" />
                      <Column field="actionNm"  header="처리 내용" />
                      <Column field="actorNm"   header="처리자"   />
                    </DataTable>
                  </template>

                  ─── #panel-files ───────────────────────────────────
                  <template #panel-files>
                    <AttachmentList :files="item.attachments" />
                  </template>
                -->
              </slot>
            </div>
          </template>
        </div>

      </div>

      <!-- ④ Actions (하단 고정 버튼 영역) -->
      <div v-if="$slots.actions" class="std-tab__actions">
        <slot name="actions">
          <!--
            예시:
            <Button label="저장"  icon="pi pi-check" :loading="saving" @click="onSave" />
            <Button label="취소"  severity="secondary" variant="outlined" @click="onCancel" />
          -->
        </slot>
      </div>

    </template>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue';

/* ────────────── Types ────────────── */
export interface TabItem {
  /** v-model 및 슬롯 이름에 사용되는 고유 키 (영문 권장) */
  key: string;
  /** 탭 버튼에 표시될 레이블 */
  label: string;
  /** 탭 버튼 뱃지 (숫자 또는 텍스트) */
  badge?: number | string;
  /** 비활성화 여부 */
  disabled?: boolean;
}

/* ────────────── Props ────────────── */
const props = withDefaults(defineProps<{
  /** 탭 목록 */
  tabs: TabItem[];
  /** 현재 활성 탭 key (v-model) */
  modelValue?: string;
  /** 데이터 로딩 중 */
  loading?: boolean;
  /** 항목 미선택 → empty 슬롯 표시 */
  isEmpty?: boolean;
  /**
   * true  → 모든 탭 패널을 DOM 에 유지 (display:none 으로 숨김)
   * false → 활성 탭 패널만 렌더링 (기본값, 성능 우선)
   */
  keepAlive?: boolean;
}>(), {
  modelValue: undefined,
  loading: false,
  isEmpty: false,
  keepAlive: false,
});

/* ────────────── Emits ────────────── */
const emit = defineEmits<{
  (e: 'update:modelValue', key: string): void;
  (e: 'tab-change', key: string): void;
}>();

/* ────────────── State ────────────── */
/** 외부 v-model 이 없으면 첫 번째 탭을 기본값으로 사용 */
const activeKey = computed(() =>
  props.modelValue ?? props.tabs[0]?.key ?? ''
);

function onTabClick(key: string) {
  if (key === activeKey.value) return;
  emit('update:modelValue', key);
  emit('tab-change', key);
}
</script>

<style scoped lang="scss">
.std-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--bg-1);

  /* 미선택 상태에서 가운데 정렬 */
  &--empty-state {
    justify-content: center;
    align-items: center;
  }

  /* ① Header */
  &__header {
    flex-shrink: 0;
    padding: 20px 24px 12px;
    border-bottom: 1px solid var(--divider-1);
  }

  /* ② Loading */
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

  /* ③ 탭 래퍼 — 남은 높이 전부 차지 */
  &__tabs-wrapper {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ── 탭 버튼 바 ──────────────────────────────────────── */
  &__tab-bar {
    flex-shrink: 0;
    display: flex;
    align-items: flex-end;
    gap: 0;
    border-bottom: 2px solid var(--divider-1);
    padding: 0 24px;
  }

  &__tab-btn {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    color: var(--txt-color-3);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
    white-space: nowrap;

    &:hover:not(:disabled) {
      color: var(--txt-color-1);
    }

    &--active {
      color: var(--brand-secondary-color);
      border-bottom-color: var(--brand-secondary-color);
      font-weight: 600;
    }

    &--disabled {
      color: var(--txt-color-4);
      cursor: not-allowed;
    }
  }

  &__tab-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    border-radius: 9px;
    background-color: var(--bg-3);
    color: var(--txt-color-3);
    font-size: 11px;
    font-weight: 600;

    .std-tab__tab-btn--active & {
      background-color: var(--brand-secondary-color);
      color: var(--txt-white-static-color);
    }
  }

  /* ── 탭 패널 영역 ──────────────────────────────────────── */
  &__panels {
    flex: 1;
    min-height: 0;
    position: relative;
  }

  &__panel {
    height: 100%;
    overflow-y: auto;
    padding: 20px 24px;

    /* keepAlive 모드: 숨김 처리 */
    &--hidden {
      display: none;
    }
  }

  /* ④ Actions — 하단 고정 */
  &__actions {
    flex-shrink: 0;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 12px 24px;
    border-top: 1px solid var(--divider-1);
    background-color: var(--bg-1);
  }

  /* 빈 상태 */
  &__empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
  }

  &__empty-default {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    color: var(--txt-color-4);

    .pi {
      font-size: 40px;
    }

    p {
      margin: 0;
      font-size: 14px;
    }
  }
}
</style>
