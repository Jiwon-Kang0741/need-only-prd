"""
Vue SFC generator — Python port of VuePageGenerator.ts + MockDataGenerator.ts.

Generates complete Vue Single-File Component code from field definitions,
supporting four page types: list-detail, list, edit, tab-detail.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# Type aliases for clarity
FieldDef = dict[str, Any]
TabDef = dict[str, Any]


# ---------------------------------------------------------------------------
#  MockDataGenerator helpers
# ---------------------------------------------------------------------------

def _mock_date(i: int) -> str:
    month = str((i % 12) + 1).zfill(2)
    day = str((i % 28) + 1).zfill(2)
    return f"2024-{month}-{day}"


def _mock_text(label: str, i: int) -> str:
    return f"{label} {i + 1}번 항목"


def _ts_type(field_type: str) -> str:
    if field_type == "number":
        return "number"
    if field_type == "checkbox":
        return "boolean"
    return "string"


def _generate_mock_assets(fields: list[FieldDef], row_count: int = 20) -> dict[str, str]:
    """Generate TypeScript interface, mock data, searchParams, and options constants."""
    data_fields = [f for f in fields if f.get("listable") or f.get("detailable")]

    # 1. TypeScript interface
    interface_lines = ["  id: number;"]
    for f in data_fields:
        interface_lines.append(f"  {f['key']}: {_ts_type(f['type'])};")
        if f["type"] in ("select", "radio", "badge"):
            interface_lines.append(f"  {f['key']}Nm: string;")
        if f["type"] == "badge":
            interface_lines.append(f"  {f['key']}Color: string;")
    interface_code = "interface RowItem {\n" + "\n".join(interface_lines) + "\n}"

    # 2. MOCK_DATA rows
    rows: list[str] = []
    for i in range(row_count):
        props = [f"id: {i + 1}"]
        for f in data_fields:
            key = f["key"]
            ft = f["type"]
            if ft in ("text", "textarea"):
                props.append(f"{key}: '{_mock_text(f['label'], i)}'")
            elif ft == "number":
                props.append(f"{key}: {(i + 1) * 1000}")
            elif ft in ("date", "daterange"):
                props.append(f"{key}: '{_mock_date(i)}'")
            elif ft in ("select", "radio", "badge"):
                opts = f.get("options") or []
                opt = opts[i % len(opts)] if opts else None
                props.append(f"{key}: '{opt['value'] if opt else ''}'")
                props.append(f"{key}Nm: '{opt['label'] if opt else ''}'")
                if ft == "badge":
                    props.append(f"{key}Color: '{opt.get('color', 'blue') if opt else 'blue'}'")
            elif ft == "checkbox":
                props.append(f"{key}: {str(i % 2 == 0).lower()}")
        rows.append(f"  {{ {', '.join(props)} }}")
    mock_data_code = "const MOCK_DATA: RowItem[] = [\n" + ",\n".join(rows) + ",\n];"

    # 3. searchParams
    search_fields = [f for f in fields if f.get("searchable")]
    search_props: list[str] = []
    for f in search_fields:
        key = f["key"]
        if f["type"] == "daterange":
            search_props.append(f"  {key}From: ''")
            search_props.append(f"  {key}To: ''")
        elif f["type"] == "number":
            search_props.append(f"  {key}: undefined as number | undefined")
        else:
            search_props.append(f"  {key}: ''")
    if search_props:
        search_params_code = "const searchParams = reactive({\n" + ",\n".join(search_props) + ",\n});"
    else:
        search_params_code = "const searchParams = reactive({});"

    # 4. options constants
    option_fields = [
        f for f in fields
        if f["type"] in ("select", "radio", "badge") and f.get("options")
    ]
    option_blocks: list[str] = []
    for f in option_fields:
        items = ",\n".join(
            f"  {{ label: '{o['label']}', value: '{o['value']}'"
            + (f", color: '{o['color']}'" if o.get("color") else "")
            + " }"
            for o in (f.get("options") or [])
        )
        option_blocks.append(
            f"const {f['key']}Options = [\n  {{ label: '\uc804\uccb4', value: '' }},\n{items},\n];"
        )
    options_code = "\n\n".join(option_blocks)

    return {
        "interfaceCode": interface_code,
        "mockDataCode": mock_data_code,
        "searchParamsCode": search_params_code,
        "optionsCode": options_code,
    }


def _generate_filter_logic(fields: list[FieldDef]) -> str:
    """Generate computed filteredRows function body."""
    search_fields = [f for f in fields if f.get("searchable")]
    checks: list[str] = []

    for f in search_fields:
        key = f["key"]
        ft = f["type"]
        if ft == "daterange":
            checks.append(f"  if (searchParams.{key}From) rows = rows.filter(r => r.{key} >= searchParams.{key}From);")
            checks.append(f"  if (searchParams.{key}To)   rows = rows.filter(r => r.{key} <= searchParams.{key}To);")
        elif ft in ("text", "textarea"):
            checks.append(f"  if (searchParams.{key}) rows = rows.filter(r => r.{key}.includes(searchParams.{key}));")
        elif ft == "number":
            checks.append(f"  if (searchParams.{key} != null) rows = rows.filter(r => r.{key} === searchParams.{key});")
        else:
            checks.append(f"  if (searchParams.{key}) rows = rows.filter(r => r.{key} === searchParams.{key});")

    if not checks:
        return "  return rows;"
    return "  let rows = allRows.value;\n" + "\n".join(checks) + "\n  return rows;"


# ---------------------------------------------------------------------------
#  Import helpers
# ---------------------------------------------------------------------------

def _collect_import_needs(fields: list[FieldDef]) -> dict[str, bool]:
    needs = {
        "Select": False,
        "InputText": False,
        "InputNumber": False,
        "RangeDatePicker": False,
        "SingleDatePicker": False,
        "Textarea": False,
        "DotStatusText": False,
    }
    for f in fields:
        if f.get("searchable") or f.get("editable"):
            ft = f["type"]
            if ft in ("select", "radio"):
                needs["Select"] = True
            if ft == "text":
                needs["InputText"] = True
            if ft == "number":
                needs["InputNumber"] = True
            if ft == "daterange":
                needs["RangeDatePicker"] = True
            if ft == "date":
                needs["SingleDatePicker"] = True
            if ft == "textarea":
                needs["Textarea"] = True
        if (f.get("listable") or f.get("detailable")) and f["type"] == "badge":
            needs["DotStatusText"] = True
    return needs


def _build_imports(needs: dict[str, bool], page_type: str) -> str:
    lines = ["import { ref, reactive, computed } from 'vue';"]

    if page_type == "list-detail":
        lines.append("import { StandardListTemplate, StandardDetailTemplate } from '@/components/templates';")
    elif page_type == "list":
        lines.append("import { StandardListTemplate } from '@/components/templates';")
    elif page_type == "edit":
        lines.append("import { StandardEditTemplate } from '@/components/templates';")
    elif page_type == "tab-detail":
        lines.append("import { StandardTabTemplate } from '@/components/templates';")
        lines.append("import type { TabItem } from '@/components/templates';")

    lines.append("import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue';")

    if page_type in ("list", "list-detail"):
        lines.append("import { SearchForm, SearchFormRow, SearchFormLabel, SearchFormField, SearchFormContent } from '@/components/common/searchForm';")
        lines.append("import { DataTable } from '@/components/common/dataTable2';")
        lines.append("import Paginator from '@/components/common/paginator/Paginator.vue';")
        lines.append("import Column from 'primevue/column';")

    # Button is always imported
    lines.append("import { Button } from '@/components/common/button';")

    if needs["Select"]:
        lines.append("import { Select } from '@/components/common/select';")
    if needs["InputText"]:
        lines.append("import { InputText } from '@/components/common/inputText';")
    if needs["InputNumber"]:
        lines.append("import { InputNumber } from '@/components/common/inputNumber';")
    if needs["RangeDatePicker"]:
        lines.append("import { RangeDatePicker } from '@/components/common/datePicker';")
    if needs["SingleDatePicker"]:
        lines.append("import { SingleDatePicker } from '@/components/common/datePicker';")
    if needs["Textarea"]:
        lines.append("import { Textarea } from '@/components/common/textarea';")
    if needs["DotStatusText"]:
        lines.append("import { DotStatusText } from '@/components/common/dotStatusText';")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Template fragment renderers
# ---------------------------------------------------------------------------

def _render_search_field(f: FieldDef) -> str:
    key = f["key"]
    label = f["label"]
    ft = f["type"]

    if ft == "text":
        control = f'<InputText v-model="searchParams.{key}" placeholder="{label} \uac80\uc0c9" style="width: var(--form-element-width)" />'
    elif ft == "number":
        control = f'<InputNumber v-model="searchParams.{key}" placeholder="{label}" style="width: var(--form-element-width)" />'
    elif ft in ("select", "radio", "badge"):
        control = f'<Select v-model="searchParams.{key}" :options="{key}Options" optionLabel="label" optionValue="value" placeholder="\uc804\uccb4" style="width: var(--form-element-width)" />'
    elif ft == "daterange":
        control = f'<RangeDatePicker v-model:from="searchParams.{key}From" v-model:to="searchParams.{key}To" />'
    elif ft == "date":
        control = f'<SingleDatePicker v-model="searchParams.{key}" style="width: var(--form-element-width)" />'
    else:
        control = f'<InputText v-model="searchParams.{key}" style="width: var(--form-element-width)" />'

    return f"""          <SearchFormLabel>{label}</SearchFormLabel>
          <SearchFormField name="{key}">
            <SearchFormContent>
              {control}
            </SearchFormContent>
          </SearchFormField>"""


def _render_column(f: FieldDef) -> str:
    key = f["key"]
    label = f["label"]
    style_attr = f' style="width: {f["width"]}"' if f.get("width") else ""

    if f["type"] == "badge":
        return f"""        <Column field="{key}Nm" header="{label}"{style_attr}>
          <template #body="{{{{ data }}}}">
            <DotStatusText :text="data.{key}Nm" :color="data.{key}Color" />
          </template>
        </Column>"""

    display_field = f"{key}Nm" if f["type"] in ("select", "radio") else key
    return f'        <Column field="{display_field}" header="{label}"{style_attr} />'


def _render_detail_row(f: FieldDef, data_ref: str) -> str:
    is_full_row = f["type"] == "textarea"
    row_class = " detail-row--full" if is_full_row else ""

    if f["type"] == "badge":
        value_content = f'<DotStatusText :text="{data_ref}?.{f["key"]}Nm" :color="{data_ref}?.{f["key"]}Color" />'
    elif f["type"] in ("select", "radio"):
        value_content = f'{{{{ {data_ref}?.{f["key"]}Nm }}}}'
    else:
        value_content = f'{{{{ {data_ref}?.{f["key"]} }}}}'

    return f"""            <div class="detail-row{row_class}">
              <span class="detail-label">{f["label"]}</span>
              <span class="detail-value">{value_content}</span>
            </div>"""


def _render_form_row(f: FieldDef) -> str:
    key = f["key"]
    label = f["label"]
    required = f.get("required", False)
    required_attr = ' class="form-label required"' if required else ' class="form-label"'
    is_full_row = f["type"] == "textarea"
    row_class = " form-row--full" if is_full_row else ""

    ft = f["type"]
    if ft == "text":
        invalid = f' :invalid="!editForm.{key}"' if required else ""
        control = f'<InputText v-model="editForm.{key}" placeholder="{label} \uc785\ub825"{invalid} />'
    elif ft == "number":
        control = f'<InputNumber v-model="editForm.{key}" />'
    elif ft in ("select", "radio", "badge"):
        invalid = f' :invalid="!editForm.{key}"' if required else ""
        control = f'<Select v-model="editForm.{key}" :options="{key}Options" optionLabel="label" optionValue="value" placeholder="\uc120\ud0dd"{invalid} />'
    elif ft == "date":
        control = f'<SingleDatePicker v-model="editForm.{key}" />'
    elif ft == "daterange":
        control = f'<RangeDatePicker v-model:from="editForm.{key}From" v-model:to="editForm.{key}To" />'
    elif ft == "textarea":
        control = f'<Textarea v-model="editForm.{key}" rows="5" autoResize placeholder="{label} \uc785\ub825" />'
    else:
        control = f'<InputText v-model="editForm.{key}" />'

    return f"""          <div class="form-row{row_class}">
            <label{required_attr}>{label}</label>
            <div class="form-control">
              {control}
            </div>
          </div>"""


# ---------------------------------------------------------------------------
#  Search params reset helper
# ---------------------------------------------------------------------------

def _search_params_reset(search_fields: list[FieldDef]) -> str:
    props = []
    for f in search_fields:
        if f["type"] == "daterange":
            props.append(f"{f['key']}From: '', {f['key']}To: ''")
        elif f["type"] == "number":
            props.append(f"{f['key']}: undefined")
        else:
            props.append(f"{f['key']}: ''")
    return "{ " + ", ".join(props) + " }"


# ---------------------------------------------------------------------------
#  Edit form props helper
# ---------------------------------------------------------------------------

def _edit_form_props(edit_fields: list[FieldDef]) -> str:
    lines = []
    for f in edit_fields:
        ft = f["type"]
        key = f["key"]
        if ft == "number":
            lines.append(f"  {key}: undefined as number | undefined")
        elif ft == "daterange":
            lines.append(f"  {key}From: ''")
            lines.append(f"  {key}To: ''")
        elif ft == "checkbox":
            lines.append(f"  {key}: false")
        else:
            lines.append(f"  {key}: ''")
    return ",\n".join(lines)


# ---------------------------------------------------------------------------
#  Page-type SFC generators
# ---------------------------------------------------------------------------

def _generate_list_detail_sfc(
    screen_id: str,
    screen_name: str,
    page_type: str,
    fields: list[FieldDef],
    menu_path: list[str] | None = None,
) -> str:
    search_fields = [f for f in fields if f.get("searchable")]
    list_fields = [f for f in fields if f.get("listable")]
    detail_fields = [f for f in fields if f.get("detailable")]
    editable_fields = [f for f in fields if f.get("editable")]

    needs = _collect_import_needs(fields)
    assets = _generate_mock_assets(fields)
    filter_logic = _generate_filter_logic(fields)
    imports = _build_imports(needs, page_type)

    menu_path_comment = " > ".join(menu_path) if menu_path else screen_name
    timestamp = datetime.now(timezone.utc).isoformat()

    search_fields_html = "\n".join(_render_search_field(f) for f in search_fields)
    columns_html = "\n".join(
        [f'        <Column field="id" header="No" style="width: 60px" />']
        + [_render_column(f) for f in list_fields]
    )
    detail_rows_html = "\n".join(_render_detail_row(f, "state.selectedRow") for f in detail_fields)

    ef = editable_fields if editable_fields else detail_fields
    edit_form_props_str = _edit_form_props(ef)
    reset = _search_params_reset(search_fields)

    return f"""<!-- Generated by pfy-scaffolding | {screen_name} ({screen_id}) | {page_type} | {timestamp} -->
<template>
  <StandardListTemplate :loading="state.loading">
    <!-- \u2460 \ud654\uba74 \uc81c\ubaa9: {menu_path_comment} -->
    <template #title>
      <ContentHeader title="{screen_name}" />
    </template>

    <!-- \u2461 \uac80\uc0c9 \uc870\uac74 \ud3fc -->
    <template #search>
      <SearchForm>
        <SearchFormRow>
{search_fields_html}
        </SearchFormRow>
        <template #buttons>
          <Button class="submit-button" label="\uc870\ud68c" icon="pi pi-search" @click="onSearch" />
          <Button label="\ucd08\uae30\ud654" severity="secondary" variant="outlined" @click="onReset" />
        </template>
      </SearchForm>
    </template>

    <!-- \u2462 \uc870\ud68c \uacb0\uacfc \uadf8\ub9ac\ub4dc (default slot) -->
    <DataTable
      :value="pagedRows"
      :loading="state.loading"
      selectionMode="single"
      v-model:selection="state.selectedRow"
      scrollable
      scrollHeight="flex"
      @row-select="onRowSelect"
    >
{columns_html}
    </DataTable>

    <!-- \u2463 \ud398\uc774\uc9c0\ub124\uc774\uc158 -->
    <template #pagination>
      <Paginator
        :rows="state.pageSize"
        :totalRecords="filteredRows.length"
        :rowsPerPageOptions="[20, 50, 100]"
        @page="onPageChange"
      />
    </template>
  </StandardListTemplate>

  <!-- \u2464 \uc0c1\uc138 \ud328\ub110 (\uc120\ud0dd\ub41c \ud589 \uc544\ub798\uc5d0 \ud45c\uc2dc) -->
  <div v-if="state.selectedRow" class="mockup-detail">
    <h3 class="mockup-detail__title">\uc0c1\uc138 \uc815\ubcf4</h3>
    <div class="mockup-detail__body">
{detail_rows_html}
    </div>
    <div class="mockup-detail__actions">
      <Button label="\uc218\uc815" icon="pi pi-pencil" severity="secondary" variant="outlined" @click="onEdit" />
      <Button label="\uc0ad\uc81c" icon="pi pi-trash" severity="danger" @click="onDelete" />
    </div>
  </div>
</template>

<script lang="ts" setup>
{imports}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Types \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
{assets['interfaceCode']}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Mock Data (API \uc5f0\ub3d9 \uc804 \uc784\uc2dc) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
{assets['mockDataCode']}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Options \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
{assets['optionsCode']}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 State \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
const allRows = ref<RowItem[]>([...MOCK_DATA]);

const state = reactive({{
  loading:     false,
  selectedRow: null as RowItem | null,
  pageSize:    20,
  page:        {{ first: 0, rows: 20 }},
}});

{assets['searchParamsCode']}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Computed \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
const filteredRows = computed<RowItem[]>(() => {{
{filter_logic}
}});

const pagedRows = computed<RowItem[]>(() =>
  filteredRows.value.slice(state.page.first, state.page.first + state.pageSize)
);

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Handlers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
function onSearch(): void {{
  state.page        = {{ first: 0, rows: state.pageSize }};
  state.selectedRow = null;
}}

function onReset(): void {{
  Object.assign(searchParams, {reset});
  onSearch();
}}

function onRowSelect(event: {{ data: RowItem }}): void {{
  state.selectedRow = event.data;
}}

function onPageChange(event: {{ first: number; rows: number }}): void {{
  state.page = event;
}}

function onEdit(): void {{
  // TODO: \uc218\uc815 \ud654\uba74\uc73c\ub85c \uc774\ub3d9 \ub610\ub294 \ubaa8\ub2ec \uc624\ud508
  console.log('[scaffold] onEdit \u2192', state.selectedRow);
}}

function onDelete(): void {{
  if (!state.selectedRow) return;
  allRows.value     = allRows.value.filter(r => r.id !== state.selectedRow!.id);
  state.selectedRow = null;
}}
</script>
"""


def _generate_edit_sfc(
    screen_id: str,
    screen_name: str,
    fields: list[FieldDef],
) -> str:
    edit_fields = [f for f in fields if f.get("editable")]
    needs = _collect_import_needs(edit_fields)
    imports = _build_imports(needs, "edit")
    assets = _generate_mock_assets(fields)
    timestamp = datetime.now(timezone.utc).isoformat()

    form_rows_html = "\n".join(_render_form_row(f) for f in edit_fields)
    efp = _edit_form_props(edit_fields)

    required_checks = "\n  ".join(
        f"if (!editForm.{f['key']}) {{ alert('{f['label']}\uc740(\ub294) \ud544\uc218 \ud56d\ubaa9\uc785\ub2c8\ub2e4.'); return; }}"
        for f in edit_fields if f.get("required")
    )

    return f"""<!-- Generated by pfy-scaffolding | {screen_name} ({screen_id}) | edit | {timestamp} -->
<template>
  <StandardEditTemplate>
    <template #title>
      <ContentHeader title="{screen_name}" />
    </template>

    <section class="form-section">
      <h3 class="form-section__title">\uae30\ubcf8 \uc815\ubcf4</h3>
{form_rows_html}
    </section>

    <template #footer-right>
      <Button label="\uc800\uc7a5" icon="pi pi-check" :loading="state.saving" @click="onSave" />
      <Button label="\ucde8\uc18c" severity="secondary" variant="outlined" @click="onCancel" />
    </template>
  </StandardEditTemplate>
</template>

<script lang="ts" setup>
{imports}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Options \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
{assets['optionsCode']}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 State \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
const state = reactive({{ loading: false, saving: false }});

const editForm = reactive({{
{efp},
}});

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Handlers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
function onSave(): void {{
  {required_checks}
  state.saving = true;
  setTimeout(() => {{
    // TODO: API \uc800\uc7a5 \ud638\ucd9c\ub85c \uad50\uccb4
    console.log('[scaffold] onSave \u2192', {{ ...editForm }});
    state.saving = false;
  }}, 800);
}}

function onCancel(): void {{
  // TODO: \uc774\uc804 \ud654\uba74\uc73c\ub85c \uc774\ub3d9
  console.log('[scaffold] onCancel');
}}
</script>
"""


def _generate_tab_detail_sfc(
    screen_id: str,
    screen_name: str,
    fields: list[FieldDef],
    tabs: list[TabDef] | None = None,
    menu_path: list[str] | None = None,
) -> str:
    tabs = tabs or []
    search_fields = [f for f in fields if f.get("searchable")]
    list_fields = [f for f in fields if f.get("listable")]

    all_tab_fields = [tf for t in tabs for tf in t.get("fields", [])]
    needs = _collect_import_needs(fields + all_tab_fields)
    imports = _build_imports(needs, "tab-detail")
    assets = _generate_mock_assets(fields)
    filter_logic = _generate_filter_logic(fields)
    timestamp = datetime.now(timezone.utc).isoformat()

    # Tab items
    tab_items_code = ",\n".join(
        f"  {{ key: '{t['key']}', label: '{t['label']}' }}" for t in tabs
    )

    # Tab panels
    tab_panels_parts = []
    for tab in tabs:
        detail_rows = "\n".join(
            _render_detail_row(f, "state.selectedRow") for f in tab.get("fields", [])
        )
        tab_panels_parts.append(
            f"    <!-- \ud0ed: {tab['label']} -->\n"
            f"    <template #panel-{tab['key']}>\n"
            f"{detail_rows}\n"
            f"    </template>"
        )
    tab_panels = "\n\n".join(tab_panels_parts)

    search_fields_html = "\n".join(_render_search_field(f) for f in search_fields)
    columns_html = "\n".join(
        [f'        <Column field="id" header="No" style="width: 60px" />']
        + [_render_column(f) for f in list_fields]
    )

    reset = _search_params_reset(search_fields)
    first_tab_key = tabs[0]["key"] if tabs else "tab0"

    return f"""<!-- Generated by pfy-scaffolding | {screen_name} ({screen_id}) | tab-detail | {timestamp} -->
<template>
  <StandardListTemplate
    :loading="state.loading"
    :isEmpty="filteredRows.length === 0 && !state.loading"
    :showRightDrawer="!!state.selectedRow"
    :listPanelSize="45"
  >
    <template #header>
      <ContentHeader title="{screen_name}" />
    </template>

    <template #search-bar>
      <SearchForm>
        <SearchFormRow>
{search_fields_html}
        </SearchFormRow>
        <template #buttons>
          <Button class="submit-button" label="\uc870\ud68c" icon="pi pi-search" @click="onSearch" />
          <Button label="\ucd08\uae30\ud654" severity="secondary" variant="outlined" @click="onReset" />
        </template>
      </SearchForm>
    </template>

    <template #grid-area>
      <DataTable
        :value="pagedRows"
        :loading="state.loading"
        selectionMode="single"
        v-model:selection="state.selectedRow"
        scrollable
        scrollHeight="flex"
        @row-select="onRowSelect"
      >
{columns_html}
      </DataTable>
    </template>

    <template #pagination>
      <Paginator
        :rows="state.pageSize"
        :totalRecords="filteredRows.length"
        :rowsPerPageOptions="[20, 50, 100]"
        @page="onPageChange"
      />
    </template>

    <!-- \uc6b0\uce21: \ud0ed\ud615 \uc0c1\uc138 \ud328\ub110 -->
    <template #right-drawer>
      <StandardTabTemplate
        v-model="state.activeTab"
        :tabs="TABS"
        :isEmpty="!state.selectedRow"
      >
        <template #header>
          <ContentHeader title="\uc0c1\uc138 \uc815\ubcf4" />
        </template>

{tab_panels}

        <template #actions>
          <Button label="\uc218\uc815" icon="pi pi-pencil" severity="secondary" variant="outlined" @click="onEdit" />
        </template>
      </StandardTabTemplate>
    </template>
  </StandardListTemplate>
</template>

<script lang="ts" setup>
{imports}
import {{ StandardTabTemplate }} from '@/components/templates';
import type {{ TabItem }} from '@/components/templates';

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Types \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
{assets['interfaceCode']}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Mock Data \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
{assets['mockDataCode']}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Options / Tabs \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
{assets['optionsCode']}

const TABS: TabItem[] = [
{tab_items_code},
];

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 State \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
const allRows = ref<RowItem[]>([...MOCK_DATA]);

const state = reactive({{
  loading:     false,
  selectedRow: null as RowItem | null,
  activeTab:   '{first_tab_key}',
  pageSize:    20,
  page:        {{ first: 0, rows: 20 }},
}});

{assets['searchParamsCode']}

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Computed \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
const filteredRows = computed<RowItem[]>(() => {{
{filter_logic}
}});

const pagedRows = computed<RowItem[]>(() =>
  filteredRows.value.slice(state.page.first, state.page.first + state.pageSize)
);

// \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Handlers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
function onSearch(): void {{
  state.page        = {{ first: 0, rows: state.pageSize }};
  state.selectedRow = null;
}}

function onReset(): void {{
  Object.assign(searchParams, {reset});
  onSearch();
}}

function onRowSelect(event: {{ data: RowItem }}): void {{
  state.selectedRow = event.data;
  state.activeTab   = '{first_tab_key}';
}}

function onPageChange(event: {{ first: number; rows: number }}): void {{
  state.page = event;
}}

function onEdit(): void {{
  console.log('[scaffold] onEdit \u2192', state.selectedRow);
}}
</script>
"""


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def generate_vue_page(
    screen_id: str,
    screen_name: str,
    page_type: str,
    fields: list[FieldDef],
    tabs: list[TabDef] | None = None,
    menu_path: list[str] | None = None,
) -> str:
    """Generate a complete Vue SFC string from field definitions.

    Args:
        screen_id: Uppercase screen ID, e.g. "MNET010".
        screen_name: Korean screen name, e.g. "신고 관리".
        page_type: One of "list-detail", "list", "edit", "tab-detail".
        fields: List of field definition dicts.
        tabs: Optional list of tab definitions (for tab-detail type).
        menu_path: Optional breadcrumb path list.

    Returns:
        Complete Vue SFC source code as a string.
    """
    if page_type in ("list-detail", "list"):
        return _generate_list_detail_sfc(screen_id, screen_name, page_type, fields, menu_path)
    elif page_type == "edit":
        return _generate_edit_sfc(screen_id, screen_name, fields)
    elif page_type == "tab-detail":
        return _generate_tab_detail_sfc(screen_id, screen_name, fields, tabs, menu_path)
    else:
        return _generate_list_detail_sfc(screen_id, screen_name, page_type, fields, menu_path)
