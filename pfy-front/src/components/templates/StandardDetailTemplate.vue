<template>
  <!--
  ┌─────────────────────────────────────────────────────────────────────┐
  │  StandardDetailTemplate — Detail Layout                             │
  │                                                                     │
  │  Layout 구조                                                         │
  │  ──────────────────────────────────────────────────────────────     │
  │  [ breadcrumb?    ]                                                 │
  │  [ title          ] [ actions-left? ] [ actions-right? ]           │
  │  [ summary?       ]  요약 정보 배너 (선택)                           │
  │  ─────────────────────────────────────────────────────             │
  │  [ default        ]  상세 필드 영역 (스크롤, flex:1)                │
  │  ─────────────────────────────────────────────────────             │
  │  [ footer-actions? ]  하단 버튼 (선택)                              │
  │                                                                     │
  │  Named Slots                                                        │
  │  ──────────────────────────────────────────────────────────────     │
  │  #title          화면/패널 제목                                      │
  │  #breadcrumb     메뉴 경로 (선택)                                    │
  │  #actions-left   제목 좌측 버튼 (선택)                               │
  │  #actions-right  제목 우측 버튼 (선택)                               │
  │  #summary        요약 정보 배너 (선택)                               │
  │  #default        읽기 전용 상세 필드 영역 (기본 슬롯)                │
  │  #footer-actions 하단 액션 버튼 (선택)                               │
  └─────────────────────────────────────────────────────────────────────┘
  -->
  <div class="std-detail">

    <!-- ── 상단 헤더 블록 ─────────────────────────────────────────────── -->
    <div class="std-detail__head">

      <!-- breadcrumb -->
      <div v-if="$slots.breadcrumb" class="std-detail__breadcrumb">
        <slot name="breadcrumb">
          <!--
            예시:
            <Breadcrumb :items="[{label:'홈'},{label:'신고 관리'}]" />
          -->
        </slot>
      </div>

      <!-- title + actions 행 -->
      <div class="std-detail__title-bar">
        <div class="std-detail__title">
          <slot name="title">
            <!--
              예시:
              <h2>신고 상세</h2>
              또는
              <ContentHeader title="신고 상세" />
            -->
          </slot>
        </div>

        <div v-if="$slots['actions-left'] || $slots['actions-right']" class="std-detail__actions">
          <div v-if="$slots['actions-left']" class="std-detail__actions-left">
            <slot name="actions-left">
              <!--
                예시:
                <Button label="목록" severity="secondary" variant="outlined" @click="onBack" />
              -->
            </slot>
          </div>
          <div v-if="$slots['actions-right']" class="std-detail__actions-right">
            <slot name="actions-right">
              <!--
                예시:
                <Button label="수정" icon="pi pi-pencil" @click="onEdit" />
                <Button label="삭제" icon="pi pi-trash" severity="danger" @click="onDelete" />
              -->
            </slot>
          </div>
        </div>
      </div>

      <!-- summary (요약 정보 배너) -->
      <div v-if="$slots.summary" class="std-detail__summary">
        <slot name="summary">
          <!--
            예시:
            <div class="summary-card">
              <DotStatusText :text="item.statusNm" :color="item.statusColor" />
              <span>{{ item.regDt }}</span>
            </div>
          -->
        </slot>
      </div>
    </div>

    <!-- ── 로딩 오버레이 ─────────────────────────────────────────────── -->
    <div v-if="loading" class="std-detail__loading" aria-live="polite">
      <i class="pi pi-spin pi-spinner" aria-hidden="true" />
      <span>불러오는 중...</span>
    </div>

    <!-- ── 상세 내용 영역 (default slot, 스크롤) ────────────────────── -->
    <div v-else class="std-detail__body">
      <slot>
        <!--
          예시 — detail-row 유틸 클래스 활용:
          <div class="detail-row">
            <span class="detail-label">처리상태</span>
            <span class="detail-value">
              <DotStatusText :text="item.statusNm" :color="item.statusColor" />
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">제목</span>
            <span class="detail-value">{{ item.title }}</span>
          </div>
          <div class="detail-row detail-row--full">
            <span class="detail-label">내용</span>
            <span class="detail-value">{{ item.content }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">등록일</span>
            <span class="detail-value">{{ item.regDt }}</span>
          </div>
        -->
      </slot>
    </div>

    <!-- ── 하단 고정 버튼 영역 ──────────────────────────────────────── -->
    <div v-if="$slots['footer-actions']" class="std-detail__footer">
      <slot name="footer-actions">
        <!--
          예시:
          <Button label="수정" icon="pi pi-pencil" @click="onEdit" />
          <Button label="삭제" icon="pi pi-trash" severity="danger" @click="onDelete" />
        -->
      </slot>
    </div>

  </div>
</template>

<script lang="ts" setup>
withDefaults(defineProps<{
  /** 상세 데이터 API 호출 중 여부 */
  loading?: boolean;
}>(), {
  loading: false,
});
</script>

<style scoped lang="scss">
.std-detail {
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
    gap: 0;
  }

  /* breadcrumb */
  &__breadcrumb {
    margin-bottom: 4px;
  }

  /* title + actions 행 */
  &__title-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 40px;
    margin-bottom: 4px;
  }

  &__title {
    flex: 1;
    min-width: 0;
  }

  &__actions {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__actions-left {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  &__actions-right {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  /* summary 배너 */
  &__summary {
    padding: 10px 0;
    border-bottom: 1px solid var(--divider-1);
    margin-bottom: 0;
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

  /* ── 상세 내용 (default slot) — 스크롤, 남은 공간 전부 ── */
  &__body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 16px 24px 20px;
  }

  /* ── 하단 고정 버튼 ── */
  &__footer {
    flex-shrink: 0;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
    padding: 12px 24px;
    border-top: 1px solid var(--divider-1);
    background-color: var(--bg-1);
  }
}

/* ──────────────────────────────────────────────────────────────────────
   #default 슬롯 내부에서 사용하는 detail-row 유틸 클래스 (deep)
   ────────────────────────────────────────────────────────────────────── */
:deep(.detail-row) {
  display: flex;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid var(--divider-1);
  gap: 16px;
  font-size: 13px;

  &.detail-row--full {
    flex-direction: column;
    gap: 6px;
  }

  .detail-label {
    flex-shrink: 0;
    width: 100px;
    font-weight: 500;
    color: var(--txt-color-3);
    padding-top: 2px;
  }

  .detail-value {
    flex: 1;
    color: var(--txt-color-1);
    word-break: break-all;
    line-height: 1.6;
  }
}
</style>
