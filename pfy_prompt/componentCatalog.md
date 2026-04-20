# Component Catalog

원본 pfy-front의 템플릿 및 공통 컴포넌트 시그니처. 
Mockup 생성 LLM은 여기 등록된 컴포넌트만 사용해야 한다.

## 페이지 템플릿 (TypeA~D)

각 생성 페이지는 반드시 아래 4개 중 하나를 상속(사용)해야 한다:

### `@/templates/TypeA_StandardSearch`

**Template 구조 (상위 40줄)**:
```vue
<div class="main-content-container">
    <ContentHeader menuId="SCREEN_ID" />

    <TypeASearchForm @search="handleSearch" />

    <TypeADataTable
      :fetchedMainData="fetchedMainData"
      :loading="loading"
    />
  </div>
```

### `@/templates/TypeB_InputDetail`

**Template 구조 (상위 40줄)**:
```vue
<div class="main-content-container">
    <ContentHeader menuId="SCREEN_ID" />

    <div class="form-page-wrapper">
      <TypeBInputForm
        :formData="formData"
        :isEditMode="isEditMode"
        :loading="loading"
        @save="handleSave"
        @cancel="handleCancel"
        @reset="handleReset"
      />
    </div>
  </div>
```

### `@/templates/TypeC_TreeGrid`

**Template 구조 (상위 40줄)**:
```vue
<div class="type-c-screen">
    <div class="type-c-header">
      <ContentHeader menuId="SCREEN_ID" />
      <TypeCSearchForm @search="handleSearch" />
    </div>

    <div class="type-c-body">
      <!-- 트리 패널 -->
      <div class="tree-panel">
        <TypeCTree
          :treeNodes="treeNodes"
          :loading="false"
          @node-select="handleNodeSelect"
          @node-unselect="handleNodeUnselect"
        />
      </div>

      <!-- 구분선 -->
      <div class="gutter" />

      <!-- 데이터 패널 -->
      <div class="data-panel">
        <TypeCDataTable
          :fetchedMainData="fetchedMainData"
          :loading="false"
          @row-dblclick="handleRowDblClick"
        />
      </div>
    </div>
  </div>
```

### `@/templates/TypeD_MasterDetail`

**Template 구조 (상위 40줄)**:
```vue
<div class="main-content-container">
    <ContentHeader menuId="SCREEN_ID" />

    <TypeDSearchForm @search="handleSearch" />

    <!-- 마스터 테이블 -->
    <section class="table-section">
      <TypeDMasterTable
        :fetchedMasterData="fetchedMasterData"
        :loading="masterLoading"
        @row-select="handleMasterRowSelect"
        @row-dblclick="handleMasterRowDblClick"
      />
    </section>

    <!-- 상세 테이블 -->
    <section class="table-section">
      <TypeDDetailTable
        :fetchedDetailData="fetchedDetailData"
        :loading="detailLoading"
      />
    </section>
  </div>
```

## 공통 컴포넌트

생성 페이지는 아래 공통 컴포넌트만 import하여 사용한다:

- `@/components/common/searchForm` → `{ default as SearchForm, default as SearchFormContent, default as SearchFormField, default as SearchFormFieldGroup, default as SearchFormLabel, default as SearchFormRow }`
- `@/components/common/dataTable2` → `{ DataTable }`
- `@/components/common/treeTable` → `{ TreeTable }`
- `@/components/common/button` → `{ Button, ToggleButton }`
- `@/components/common/select` → `{ Select }`
- `@/components/common/inputText` → `{ InputText }`
- `@/components/common/inputNumber` → `{ InputNumber }`
- `@/components/common/datePicker` → `{ DatePicker, RangeDatePicker, SingleDatePicker }`
- `@/components/common/textarea` → `{ Textarea }`
- `@/components/common/contentHeader` → `ContentHeader.vue`
- `@/components/common/paginator` → `Paginator.vue`
- `@/components/common/splitter` → `Splitter, SplitterPanel.vue`
- `@/components/common/radioButton` → `{ RadioButton, RadioButtonGroup, RadioButtonWrapper }`
- `@/components/common/toggleSwitch` → `{ ToggleSwitch }`