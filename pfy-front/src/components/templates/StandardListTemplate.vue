<template>
  <!--
  ┌─────────────────────────────────────────────────────────────────────┐
  │  StandardListTemplate — List Layout                                 │
  │                                                                     │
  │  Layout 구조                                                         │
  │  ──────────────────────────────────────────────────────────────     │
  │  [ breadcrumb? ]                                                    │
  │  [ title       ] [ actions-left? ] [ actions-right? ]              │
  │  [ search?     ]                                                    │
  │  ─────────────────────────────────────────────────────             │
  │  [ default     ]  그리드 / 테이블 영역 (flex: 1)                    │
  │  ─────────────────────────────────────────────────────             │
  │  [ pagination? ]                                                    │
  │                                                                     │
  │  Named Slots                                                        │
  │  ──────────────────────────────────────────────────────────────     │
  │  #title         화면 제목                                            │
  │  #breadcrumb    메뉴 경로 (선택)                                      │
  │  #search        검색 조건 폼 (선택)                                   │
  │  #actions-left  제목 좌측 버튼 영역 (선택)                            │
  │  #actions-right 제목 우측 버튼 영역 (선택)                            │
  │  #default       조회 결과 그리드 (기본 슬롯)                          │
  │  #pagination    페이지 네비게이션 (선택)                              │
  └─────────────────────────────────────────────────────────────────────┘
  -->
  <div class="std-list">

    <!-- ── 상단 헤더 블록 ─────────────────────────────────────────────── -->
    <div class="std-list__head">

      <!-- breadcrumb -->
      <div v-if="$slots.breadcrumb" class="std-list__breadcrumb">
        <slot name="breadcrumb">
          <!--
            예시:
            <Breadcrumb :items="[{label:'홈'},{label:'업무관리'},{label:'신고 관리'}]" />
          -->
        </slot>
      </div>

      <!-- title + action bar -->
      <div class="std-list__title-bar">
        <div class="std-list__title">
          <slot name="title">
            <!--
              예시:
              <h2>신고 관리</h2>
              또는
              <ContentHeader title="신고 관리" />
            -->
          </slot>
        </div>

        <div v-if="$slots['actions-left'] || $slots['actions-right']" class="std-list__actions">
          <div v-if="$slots['actions-left']" class="std-list__actions-left">
            <slot name="actions-left">
              <!--
                예시:
                <Button label="일괄삭제" severity="danger" variant="outlined" />
              -->
            </slot>
          </div>
          <div v-if="$slots['actions-right']" class="std-list__actions-right">
            <slot name="actions-right">
              <!--
                예시:
                <Button label="등록" icon="pi pi-plus" @click="onCreate" />
                <Button label="엑셀 다운로드" icon="pi pi-download" severity="secondary" />
              -->
            </slot>
          </div>
        </div>
      </div>

      <!-- search -->
      <div v-if="$slots.search" class="std-list__search">
        <slot name="search">
          <!--
            예시:
            <SearchForm>
              <SearchFormRow>
                <SearchFormLabel>처리상태</SearchFormLabel>
                <SearchFormField name="status">
                  <SearchFormContent>
                    <Select v-model="params.status" :options="statusOptions" placeholder="전체" />
                  </SearchFormContent>
                </SearchFormField>
              </SearchFormRow>
              <template #buttons>
                <Button class="submit-button" label="조회" icon="pi pi-search" @click="onSearch" />
                <Button label="초기화" severity="secondary" variant="outlined" @click="onReset" />
              </template>
            </SearchForm>
          -->
        </slot>
      </div>
    </div>

    <!-- ── 그리드 영역 (default slot) ───────────────────────────────── -->
    <div class="std-list__body">
      <slot>
        <!--
          예시:
          <DataTable
            :value="rows"
            :loading="loading"
            selectionMode="single"
            v-model:selection="selectedRow"
            scrollable
            scrollHeight="flex"
          >
            <Column field="id"       header="No"       style="width:60px" />
            <Column field="title"    header="제목" />
            <Column field="statusNm" header="처리상태" style="width:100px" />
            <Column field="regDt"    header="등록일"   style="width:120px" />
          </DataTable>
        -->
      </slot>
    </div>

    <!-- ── 페이지네이션 ──────────────────────────────────────────────── -->
    <div v-if="$slots.pagination" class="std-list__pagination">
      <slot name="pagination">
        <!--
          예시:
          <Paginator
            :rows="pageSize"
            :totalRecords="totalCount"
            :rowsPerPageOptions="[20, 50, 100]"
            @page="onPageChange"
          />
        -->
      </slot>
    </div>

  </div>
</template>

<script lang="ts" setup>
withDefaults(defineProps<{
  /** 그리드 로딩 중 여부. DataTable 의 :loading prop 과 함께 사용 */
  loading?: boolean;
}>(), {
  loading: false,
});
</script>

<style scoped lang="scss">
.std-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px 24px;
  background-color: var(--bg-1);
  overflow: hidden;
  box-sizing: border-box;

  /* ── 상단 헤더 블록 ── */
  &__head {
    flex-shrink: 0;
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
    margin-bottom: 8px;
  }

  &__title {
    flex: 1;
    min-width: 0;
  }

  /* actions (좌+우 묶음) */
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

  /* search */
  &__search {
    flex-shrink: 0;
    margin-bottom: 8px;
  }

  /* ── 그리드 영역 (flex: 1, 내부 스크롤은 DataTable 이 처리) ── */
  &__body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* ── 페이지네이션 ── */
  &__pagination {
    flex-shrink: 0;
    padding-top: 8px;
    border-top: 1px solid var(--divider-1);
  }
}
</style>
