<template>
  <div class="mockup-banner">🖼 Mockup - ProjectMockup</div>

  <div class="mockup-layout">
    <aside class="sidebar">
      <div class="sidebar-title">화면 메뉴</div>
      <button
        v-for="screen in screens"
        :key="screen.id"
        class="sidebar-menu"
        :class="{ active: currentScreen === screen.id }"
        @click="currentScreen = screen.id"
      >
        {{ screen.label }}
      </button>
    </aside>

    <section class="content-area">
      <div class="topbar">
        <div class="topbar-title">인터뷰용 시연 목업</div>
        <div class="role-switcher">
          <span class="role-label">역할 전환</span>
          <Select
            v-model="currentRole"
            :options="roles"
            optionLabel="label"
            optionValue="value"
            placeholder="역할 선택"
          />
        </div>
      </div>

      <div v-if="currentScreen === 'screen1'" class="main-content-container">
        <ContentHeader menuId="SCREEN_1" />

        <SearchForm @submit="searchScreen1" @reset="resetScreen1">
          <SearchFormRow>
            <SearchFormField name="keyword">
              <SearchFormLabel>검색어</SearchFormLabel>
              <InputText v-model="screen1Search.keyword" placeholder="이름 또는 코드" />
            </SearchFormField>
            <SearchFormField name="status">
              <SearchFormLabel>상태</SearchFormLabel>
              <Select
                v-model="screen1Search.status"
                :options="statusOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="전체"
              />
            </SearchFormField>
          </SearchFormRow>
        </SearchForm>

        <div class="table-header">
          <div class="table-title">[화면 1] 목록</div>
          <div class="table-actions">
            <Button v-show="currentRole === 'ADMIN'" @click="openCreateDialog">등록</Button>
          </div>
        </div>

        <table class="mock-table">
          <thead>
            <tr>
              <th>코드</th>
              <th>이름</th>
              <th>상태</th>
              <th>담당자</th>
              <th>등록일</th>
              <th>관리</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in filteredScreen1Rows"
              :key="row.id"
              @click="openDetailDialog(row)"
              class="clickable-row"
            >
              <td>{{ row.code }}</td>
              <td>{{ row.name }}</td>
              <td>{{ row.status }}</td>
              <td>{{ row.owner }}</td>
              <td>{{ row.createdAt }}</td>
              <td @click.stop>
                <div class="row-actions">
                  <Button v-show="currentRole === 'ADMIN'" @click="openEditDialog(row)">수정</Button>
                  <Button v-show="currentRole === 'ADMIN'" @click="openDeleteDialog(row)">삭제</Button>
                  <Button @click="openDetailDialog(row)">상세</Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <Paginator
          :totalRecords="filteredScreen1Rows.length"
          :rows="5"
          :first="0"
          @page="() => {}"
        />
      </div>

      <div v-if="currentScreen === 'screen2'" class="main-content-container">
        <ContentHeader menuId="SCREEN_2" />

        <SearchForm @submit="searchScreen2" @reset="resetScreen2">
          <SearchFormRow>
            <SearchFormField name="category">
              <SearchFormLabel>분류</SearchFormLabel>
              <Select
                v-model="screen2Search.category"
                :options="categoryOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="전체"
              />
            </SearchFormField>
            <SearchFormField name="date">
              <SearchFormLabel>기준일</SearchFormLabel>
              <SingleDatePicker v-model="screen2Search.date" />
            </SearchFormField>
          </SearchFormRow>
        </SearchForm>

        <section class="table-section">
          <div class="table-title">[화면 2] 마스터 목록</div>
          <table class="mock-table">
            <thead>
              <tr>
                <th>구분</th>
                <th>제목</th>
                <th>작성자</th>
                <th>진행상태</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="master in filteredMasterRows"
                :key="master.id"
                class="clickable-row"
                :class="{ selected: selectedMaster && selectedMaster.id === master.id }"
                @click="selectMaster(master)"
              >
                <td>{{ master.category }}</td>
                <td>{{ master.title }}</td>
                <td>{{ master.writer }}</td>
                <td>{{ master.status }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="table-section">
          <div class="table-title">[화면 2] 상세 정보</div>
          <table class="mock-table">
            <thead>
              <tr>
                <th>항목</th>
                <th>값</th>
                <th>비고</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="detail in selectedMasterDetails" :key="detail.id">
                <td>{{ detail.item }}</td>
                <td>{{ detail.value }}</td>
                <td>{{ detail.note }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <div v-if="currentScreen === 'screen3'" class="main-content-container">
        <ContentHeader menuId="SCREEN_3" />

        <div class="form-page-wrapper">
          <div class="form-card">
            <div class="form-title">[화면 3] 등록/수정 폼</div>

            <div class="form-grid">
              <div class="form-field">
                <label>제목</label>
                <InputText v-model="screen3Form.title" placeholder="제목 입력" />
              </div>
              <div class="form-field">
                <label>유형</label>
                <Select
                  v-model="screen3Form.type"
                  :options="typeOptions"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="유형 선택"
                />
              </div>
              <div class="form-field">
                <label>수량</label>
                <InputNumber v-model="screen3Form.quantity" :min="0" />
              </div>
              <div class="form-field">
                <label>사용 여부</label>
                <ToggleSwitch v-model="screen3Form.enabled" />
              </div>
              <div class="form-field full">
                <label>설명</label>
                <Textarea v-model="screen3Form.description" :rows="5" />
              </div>
            </div>

            <div class="form-actions">
              <Button v-show="currentRole === 'ADMIN'" @click="saveScreen3">저장</Button>
              <Button @click="resetScreen3">초기화</Button>
            </div>

            <div class="sample-list-title">최근 등록 데이터</div>
            <table class="mock-table">
              <thead>
                <tr>
                  <th>제목</th>
                  <th>유형</th>
                  <th>수량</th>
                  <th>사용 여부</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in recentFormRows" :key="item.id">
                  <td>{{ item.title }}</td>
                  <td>{{ item.type }}</td>
                  <td>{{ item.quantity }}</td>
                  <td>{{ item.enabled ? '사용' : '미사용' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <div v-if="showDetailDialog" class="dialog-backdrop" @click="showDetailDialog = false">
      <div class="dialog-panel" @click.stop>
        <div class="dialog-header">
          <strong>상세 정보</strong>
          <button class="close-btn" @click="showDetailDialog = false">닫기</button>
        </div>
        <div class="dialog-body" v-if="selectedRow">
          <p><b>코드:</b> {{ selectedRow.code }}</p>
          <p><b>이름:</b> {{ selectedRow.name }}</p>
          <p><b>상태:</b> {{ selectedRow.status }}</p>
          <p><b>담당자:</b> {{ selectedRow.owner }}</p>
          <p><b>설명:</b> {{ selectedRow.description }}</p>
        </div>
      </div>
    </div>

    <div v-if="showEditDialog" class="dialog-backdrop" @click="showEditDialog = false">
      <div class="dialog-panel" @click.stop>
        <div class="dialog-header">
          <strong>{{ editMode === 'create' ? '신규 등록' : '정보 수정' }}</strong>
          <button class="close-btn" @click="showEditDialog = false">닫기</button>
        </div>
        <div class="dialog-body">
          <div class="form-grid">
            <div class="form-field">
              <label>코드</label>
              <InputText v-model="editForm.code" />
            </div>
            <div class="form-field">
              <label>이름</label>
              <InputText v-model="editForm.name" />
            </div>
            <div class="form-field">
              <label>상태</label>
              <Select
                v-model="editForm.status"
                :options="statusOptions"
                optionLabel="label"
                optionValue="value"
              />
            </div>
            <div class="form-field">
              <label>담당자</label>
              <InputText v-model="editForm.owner" />
            </div>
            <div class="form-field full">
              <label>설명</label>
              <Textarea v-model="editForm.description" :rows="4" />
            </div>
          </div>
          <div class="form-actions">
            <Button @click="saveEditForm">저장</Button>
            <Button @click="showEditDialog = false">취소</Button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showDeleteConfirm" class="dialog-backdrop" @click="showDeleteConfirm = false">
      <div class="dialog-panel small" @click.stop>
        <div class="dialog-header">
          <strong>삭제 확인</strong>
          <button class="close-btn" @click="showDeleteConfirm = false">닫기</button>
        </div>
        <div class="dialog-body">
          <p v-if="selectedRow">선택한 항목 "{{ selectedRow.name }}" 을(를) 삭제하시겠습니까?</p>
          <div class="form-actions">
            <Button @click="confirmDelete">삭제</Button>
            <Button @click="showDeleteConfirm = false">취소</Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import SearchForm from '@/components/common/searchForm/SearchForm.vue'
import SearchFormRow from '@/components/common/searchForm/SearchFormRow.vue'
import SearchFormField from '@/components/common/searchForm/SearchFormField.vue'
import SearchFormLabel from '@/components/common/searchForm/SearchFormLabel.vue'
import { Select } from '@/components/common/select'
import { InputText } from '@/components/common/inputText'
import { InputNumber } from '@/components/common/inputNumber'
import { SingleDatePicker } from '@/components/common/datePicker'
import { Textarea } from '@/components/common/textarea'
import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue'
import Paginator from '@/components/common/paginator/Paginator.vue'
import { Button } from '@/components/common/button'
import { ToggleSwitch } from '@/components/common/toggleSwitch'

const screens = [
  { id: 'screen1', label: '[화면 1]' },
  { id: 'screen2', label: '[화면 2]' },
  { id: 'screen3', label: '[화면 3]' },
]

const roles = [
  { label: 'ADMIN', value: 'ADMIN' },
  { label: 'USER', value: 'USER' },
]

const statusOptions = [
  { label: '전체', value: '' },
  { label: '사용', value: '사용' },
  { label: '대기', value: '대기' },
  { label: '중지', value: '중지' },
]

const categoryOptions = [
  { label: '전체', value: '' },
  { label: '기획', value: '기획' },
  { label: '운영', value: '운영' },
  { label: '개발', value: '개발' },
]

const typeOptions = [
  { label: '유형 A', value: '유형 A' },
  { label: '유형 B', value: '유형 B' },
  { label: '유형 C', value: '유형 C' },
]

const currentScreen = ref('screen1')
const currentRole = ref('ADMIN')

const showDetailDialog = ref(false)
const showEditDialog = ref(false)
const showDeleteConfirm = ref(false)
const selectedRow = ref(null)
const selectedMaster = ref(null)
const editMode = ref('create')

const screen1Search = reactive({
  keyword: '',
  status: '',
})

const screen2Search = reactive({
  category: '',
  date: new Date(),
})

const screen3Form = reactive({
  title: '샘플 등록 데이터',
  type: '유형 A',
  quantity: 25,
  enabled: true,
  description: '고객 인터뷰 시연용 기본 설명 데이터입니다.',
})

const screen1Rows = ref([
  { id: 1, code: 'PRJ-001', name: '기본 설정 관리', status: '사용', owner: '김민수', createdAt: '2026-04-01', description: '기본 코드와 환경설정을 관리합니다.' },
  { id: 2, code: 'PRJ-002', name: '사용자 요청 처리', status: '대기', owner: '이서연', createdAt: '2026-04-03', description: '사용자 접수 요청을 확인하고 배정합니다.' },
  { id: 3, code: 'PRJ-003', name: '월간 현황 집계', status: '사용', owner: '박지훈', createdAt: '2026-04-07', description: '월별 운영 현황과 통계를 조회합니다.' },
  { id: 4, code: 'PRJ-004', name: '알림 발송 관리', status: '중지', owner: '최유진', createdAt: '2026-04-09', description: '시스템 알림 발송 정책을 설정합니다.' },
  { id: 5, code: 'PRJ-005', name: '권한 검토 프로세스', status: '사용', owner: '정하늘', createdAt: '2026-04-12', description: '권한 신청과 승인 단계를 관리합니다.' },
])

const masterRows = ref([
  { id: 1, category: '기획', title: '서비스 개선안 검토', writer: '김민수', status: '진행중' },
  { id: 2, category: '운영', title: '월간 운영 리포트', writer: '이서연', status: '완료' },
  { id: 3, category: '개발', title: '배포 일정 협의', writer: '박지훈', status: '대기' },
  { id: 4, category: '기획', title: '고객 인터뷰 정리', writer: '최유진', status: '완료' },
])

const detailMap = {
  1: [
    { id: 11, item: '우선순위', value: '상', note: '2분기 내 반영 예정' },
    { id: 12, item: '협업부서', value: '운영팀', note: '주 1회 정기 회의' },
    { id: 13, item: '예상효과', value: '처리시간 20% 단축', note: '업무 표준화 기대' },
  ],
  2: [
    { id: 21, item: '작성주기', value: '월 1회', note: '매월 첫째 주' },
    { id: 22, item: '대상범위', value: '전사 운영 현황', note: '부서별 수치 포함' },
    { id: 23, item: '보고대상', value: '관리자', note: 'PDF 공유' },
  ],
  3: [
    { id: 31, item: '배포환경', value: '운영/스테이징', note: '사전 점검 필요' },
    { id: 32, item: '예정일', value: '2026-04-25', note: '야간 배포' },
    { id: 33, item: '담당개발자', value: '박지훈', note: '배포 체크리스트 보유' },
  ],
  4: [
    { id: 41, item: '인터뷰 수', value: '5건', note: '핵심 요구사항 정리' },
    { id: 42, item: '주요이슈', value: '조회속도, 권한', note: '차기 버전 검토' },
    { id: 43, item: '후속조치', value: '목업 보완', note: '추가 의견 반영 예정' },
  ],
}

const recentFormRows = ref([
  { id: 1, title: '샘플 데이터 1', type: '유형 A', quantity: 10, enabled: true },
  { id: 2, title: '샘플 데이터 2', type: '유형 B', quantity: 18, enabled: false },
  { id: 3, title: '샘플 데이터 3', type: '유형 C', quantity: 7, enabled: true },
  { id: 4, title: '샘플 데이터 4', type: '유형 A', quantity: 22, enabled: true },
])

const editForm = reactive({
  id: null,
  code: '',
  name: '',
  status: '사용',
  owner: '',
  description: '',
})

const filteredScreen1Rows = computed(() => {
  return screen1Rows.value.filter((row) => {
    const keywordMatch =
      !screen1Search.keyword ||
      row.name.includes(screen1Search.keyword) ||
      row.code.includes(screen1Search.keyword)
    const statusMatch = !screen1Search.status || row.status === screen1Search.status
    return keywordMatch && statusMatch
  })
})

const filteredMasterRows = computed(() => {
  return masterRows.value.filter((row) => {
    return !screen2Search.category || row.category === screen2Search.category
  })
})

const selectedMasterDetails = computed(() => {
  if (!selectedMaster.value) return []
  return detailMap[selectedMaster.value.id] || []
})

function searchScreen1() {}
function resetScreen1() {
  screen1Search.keyword = ''
  screen1Search.status = ''
}

function searchScreen2() {}
function resetScreen2() {
  screen2Search.category = ''
  screen2Search.date = new Date()
}

function openDetailDialog(row) {
  selectedRow.value = row
  showDetailDialog.value = true
}

function openCreateDialog() {
  editMode.value = 'create'
  editForm.id = null
  editForm.code = `PRJ-00${screen1Rows.value.length + 1}`
  editForm.name = ''
  editForm.status = '사용'
  editForm.owner = ''
  editForm.description = ''
  showEditDialog.value = true
}

function openEditDialog(row) {
  editMode.value = 'edit'
  selectedRow.value = row
  editForm.id = row.id
  editForm.code = row.code
  editForm.name = row.name
  editForm.status = row.status
  editForm.owner = row.owner
  editForm.description = row.description
  showEditDialog.value = true
}

function saveEditForm() {
  if (editMode.value === 'create') {
    screen1Rows.value.unshift({
      id: Date.now(),
      code: editForm.code,
      name: editForm.name || '신규 항목',
      status: editForm.status,
      owner: editForm.owner || '미지정',
      createdAt: '2026-04-21',
      description: editForm.description || '신규 등록 데이터입니다.',
    })
  } else {
    const target = screen1Rows.value.find((item) => item.id === editForm.id)
    if (target) {
      target.code = editForm.code
      target.name = editForm.name
      target.status = editForm.status
      target.owner = editForm.owner
      target.description = editForm.description
    }
  }
  showEditDialog.value = false
}

function openDeleteDialog(row) {
  selectedRow.value = row
  showDeleteConfirm.value = true
}

function confirmDelete() {
  screen1Rows.value = screen1Rows.value.filter((item) => item.id !== selectedRow.value.id)
  showDeleteConfirm.value = false
  selectedRow.value = null
}

function selectMaster(master) {
  selectedMaster.value = master
}

function saveScreen3() {
  recentFormRows.value.unshift({
    id: Date.now(),
    title: screen3Form.title,
    type: screen3Form.type,
    quantity: screen3Form.quantity,
    enabled: screen3Form.enabled,
  })
}

function resetScreen3() {
  screen3Form.title = '샘플 등록 데이터'
  screen3Form.type = '유형 A'
  screen3Form.quantity = 25
  screen3Form.enabled = true
  screen3Form.description = '고객 인터뷰 시연용 기본 설명 데이터입니다.'
}

selectedMaster.value = masterRows.value[0]
</script>

<style scoped>
.mockup-banner {
  background: #111827;
  color: #fff;
  padding: 12px 16px;
  font-weight: 700;
}

.mockup-layout {
  display: flex;
  min-height: calc(100vh - 48px);
  background: #f5f7fb;
}

.sidebar {
  width: 220px;
  background: #ffffff;
  border-right: 1px solid #dbe2ea;
  padding: 16px;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 12px;
}

.sidebar-menu {
  width: 100%;
  text-align: left;
  margin-bottom: 8px;
  padding: 10px 12px;
  border: 1px solid #dbe2ea;
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
}

.sidebar-menu.active {
  background: #e8f0ff;
  border-color: #7aa2ff;
}

.content-area {
  flex: 1;
  padding: 16px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.topbar-title {
  font-size: 18px;
  font-weight: 700;
}

.role-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 240px;
}

.role-label {
  font-size: 13px;
  color: #4b5563;
  white-space: nowrap;
}

.table-header,
.table-actions,
.form-actions,
.row-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.table-header {
  justify-content: space-between;
  margin: 16px 0 8px;
}

.table-title,
.form-title,
.sample-list-title {
  font-size: 16px;
  font-weight: 700;
  margin: 12px 0;
}

.mock-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  margin-bottom: 16px;
}

.mock-table th,
.mock-table td {
  border: 1px solid #dbe2ea;
  padding: 10px;
  text-align: left;
  font-size: 14px;
}

.clickable-row {
  cursor: pointer;
}

.clickable-row:hover {
  background: #f9fbff;
}

.selected {
  background: #eef4ff;
}

.form-page-wrapper {
  padding: 8px 0;
}

.form-card {
  background: #fff;
  border: 1px solid #dbe2ea;
  border-radius: 12px;
  padding: 20px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-field.full {
  grid-column: 1 / -1;
}

.table-section {
  margin-top: 16px;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog-panel {
  width: 640px;
  max-width: calc(100vw - 32px);
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}

.dialog-panel.small {
  width: 420px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f3f6fb;
  border-bottom: 1px solid #dbe2ea;
}

.dialog-body {
  padding: 16px;
}

.close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
}

@media (max-width: 960px) {
  .mockup-layout {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>