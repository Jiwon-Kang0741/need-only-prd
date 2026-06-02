/**
 * MenuTreeManagement.tsx
 * 메뉴 트리 그리드 관리 화면
 * AG Grid Community v35 (treeData Enterprise 미사용 — 직접 트리 렌더링)
 *
 * [설치]  cd frontend && npm install ag-grid-community ag-grid-react
 */
import React, {
  useState,
  useMemo,
  useCallback,
  useRef,
  useEffect,
  forwardRef,
  useImperativeHandle,
} from 'react';
import { AgGridReact } from 'ag-grid-react';
import { AllCommunityModule, ModuleRegistry, themeQuartz } from 'ag-grid-community';
import type {
  ColDef,
  GridApi,
  GridReadyEvent,
  RowDragEndEvent,
  CellValueChangedEvent,
  ICellRendererParams,
  ICellEditorParams,
} from 'ag-grid-community';

ModuleRegistry.registerModules([AllCommunityModule]);

// ── AG Grid v33+ Theme API (CSS 파일 import 불필요) ──
const darkTheme = themeQuartz.withParams({
  accentColor: '#f4821f',
  backgroundColor: '#1a1a1a',
  foregroundColor: '#e5e7eb',
  headerBackgroundColor: '#111111',
  headerTextColor: '#9ca3af',
  rowHoverColor: '#242424',
  selectedRowBackgroundColor: 'rgba(244,130,31,0.13)',
  borderColor: '#2a2a2a',
  rowBorder: { color: '#222222', width: 1 },
  columnBorder: { color: '#222222', width: 1 },
  fontSize: 13,
  fontFamily: 'system-ui, sans-serif',
});

// 스크롤바 + 선택 행 좌측 포인트 스타일
const EXTRA_CSS = `
  .ag-menu-wrap ::-webkit-scrollbar { width: 6px; height: 6px; }
  .ag-menu-wrap ::-webkit-scrollbar-track { background: #111111; }
  .ag-menu-wrap ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
  .ag-menu-wrap ::-webkit-scrollbar-thumb:hover { background: #f4821f; }
`;

// ─────────────────────────────────────────────
// 데이터 모델
// ─────────────────────────────────────────────
// 역할(권한) 정의
// ─────────────────────────────────────────────
const ROLES = [
  { value: 'ITO_ADM',  label: '시스템관리자', color: '#f4821f', bg: 'rgba(244,130,31,0.15)'  },
  { value: 'GEN_USER', label: '일반사용자',   color: '#60a5fa', bg: 'rgba(96,165,250,0.15)'  },
  { value: 'BUS_ADM',  label: '현업담당자',   color: '#4ade80', bg: 'rgba(74,222,128,0.15)'  },
] as const;
type RoleValue = typeof ROLES[number]['value'];
const ROLE_VALUES = new Set<RoleValue>(ROLES.map((r) => r.value));

// ─────────────────────────────────────────────
interface MenuRow {
  menuId: string;
  menuName: string;
  parentId: string; // 최상위 = "ROOT"
  sortOrder: number;
  menuType: 'FOLDER' | 'PROGRAM';
  componentKey?: string | null;
  useYn: 'Y' | 'N';
  roles: RoleValue[];  // 접근 가능 역할 목록
}

function normalizeRoles(input: unknown): RoleValue[] {
  if (!Array.isArray(input)) return [];
  return input.filter((v): v is RoleValue => typeof v === 'string' && ROLE_VALUES.has(v as RoleValue));
}

function normalizeMenuRows(rows: MenuRow[]): MenuRow[] {
  return rows.map((r) => ({ ...r, roles: normalizeRoles((r as MenuRow).roles) }));
}

// 그리드 표시용 (level + hasChildren 추가, 상태 저장 금지)
interface MenuRowVM extends MenuRow {
  level: number;
  hasChildren: boolean;
}

const ROOT_ID = 'ROOT';

// ─────────────────────────────────────────────
// 초기 목 데이터  (ID 규칙: ROOT01, ROOT0101, ROOT010101…)
// ─────────────────────────────────────────────
const INITIAL_MENU: MenuRow[] = [
  { menuId: 'ROOT01',   menuName: '교육 관리',         parentId: ROOT_ID,  sortOrder: 1, menuType: 'FOLDER',  useYn: 'Y', roles: ['ITO_ADM', 'GEN_USER', 'BUS_ADM'] },
  { menuId: 'ROOT02',   menuName: '시스템 관리',        parentId: ROOT_ID,  sortOrder: 2, menuType: 'FOLDER',  useYn: 'Y', roles: ['ITO_ADM'] },
  { menuId: 'ROOT0101', menuName: '교육 프로그램 목록', parentId: 'ROOT01', sortOrder: 1, menuType: 'PROGRAM', componentKey: 'EduProgramList', useYn: 'Y', roles: ['ITO_ADM', 'GEN_USER', 'BUS_ADM'] },
  { menuId: 'ROOT0102', menuName: '교육 실적 조회',     parentId: 'ROOT01', sortOrder: 2, menuType: 'PROGRAM', componentKey: 'EduResultList',  useYn: 'Y', roles: ['ITO_ADM', 'BUS_ADM'] },
  { menuId: 'ROOT0201', menuName: '메뉴 관리',          parentId: 'ROOT02', sortOrder: 1, menuType: 'PROGRAM', useYn: 'Y', roles: ['ITO_ADM'] },
  { menuId: 'ROOT0202', menuName: '권한 관리',          parentId: 'ROOT02', sortOrder: 2, menuType: 'PROGRAM', useYn: 'Y', roles: ['ITO_ADM'] },
];

// ─────────────────────────────────────────────
// 유틸
// ─────────────────────────────────────────────
function buildChildMap(rows: MenuRow[]): Map<string, MenuRow[]> {
  const map = new Map<string, MenuRow[]>();
  rows.forEach((r) => {
    const list = map.get(r.parentId) ?? [];
    list.push(r);
    map.set(r.parentId, list);
  });
  map.forEach((v) => v.sort((a, b) => a.sortOrder - b.sortOrder));
  return map;
}

/** Flat array → 표시 순서 뷰모델 (expandedIds 기반 가시성 처리) */
function buildVisibleRows(rows: MenuRow[], expandedIds: Set<string>): MenuRowVM[] {
  const childMap = buildChildMap(rows);
  const result: MenuRowVM[] = [];

  function traverse(parentId: string, level: number) {
    const children = childMap.get(parentId) ?? [];
    children.forEach((row) => {
      const kids = childMap.get(row.menuId) ?? [];
      result.push({ ...row, level, hasChildren: kids.length > 0 });
      if (kids.length > 0 && expandedIds.has(row.menuId)) {
        traverse(row.menuId, level + 1);
      }
    });
  }

  traverse(ROOT_ID, 0);
  return result;
}

function isDescendant(rows: MenuRow[], sourceId: string, targetId: string): boolean {
  const childMap = buildChildMap(rows);
  function dfs(id: string): boolean {
    if (id === targetId) return true;
    return (childMap.get(id) ?? []).some((c) => dfs(c.menuId));
  }
  return dfs(sourceId);
}

function reorderSiblings(rows: MenuRow[], parentId: string): MenuRow[] {
  const sibs = rows.filter((r) => r.parentId === parentId).sort((a, b) => a.sortOrder - b.sortOrder);
  const sibIds = new Set(sibs.map((s) => s.menuId));
  return rows.map((r) =>
    sibIds.has(r.menuId) ? { ...r, sortOrder: sibs.findIndex((s) => s.menuId === r.menuId) + 1 } : r,
  );
}

/**
 * 트리 전체를 순회해 새 ID 매핑을 생성한다.
 * ROOT 레벨: ROOT01, ROOT02 …
 * 하위 레벨: 부모ID + 2자리 순번 (ROOT0101, ROOT010101 …)
 */
function buildIdMap(rows: MenuRow[]): Map<string, string> {
  const idMap = new Map<string, string>();
  function visit(parentId: string, prefix: string) {
    rows
      .filter((r) => r.parentId === parentId)
      .sort((a, b) => a.sortOrder - b.sortOrder)
      .forEach((child, idx) => {
        const newId = `${prefix}${String(idx + 1).padStart(2, '0')}`;
        idMap.set(child.menuId, newId);
        visit(child.menuId, newId);
      });
  }
  visit(ROOT_ID, 'ROOT');
  return idMap;
}

function applyIdMap(rows: MenuRow[], idMap: Map<string, string>): MenuRow[] {
  return rows.map((r) => ({
    ...r,
    menuId:   idMap.get(r.menuId)   ?? r.menuId,
    parentId: r.parentId === ROOT_ID ? ROOT_ID : (idMap.get(r.parentId) ?? r.parentId),
  }));
}


// ─────────────────────────────────────────────
// API — 서버 파일 영구 저장 (backend/data/menu_tree.json)
// ─────────────────────────────────────────────
const API_BASE = '/api';

async function fetchMenuTree(): Promise<MenuRow[] | null> {
  try {
    const res = await fetch(`${API_BASE}/menu-tree`);
    if (!res.ok) return null;
    const data = await res.json() as { rows: MenuRow[] };
    return data.rows?.length ? normalizeMenuRows(data.rows) : null;
  } catch {
    return null;
  }
}

async function postMenuTree(rows: MenuRow[]): Promise<void> {
  const res = await fetch(`${API_BASE}/menu-tree`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rows }),
  });
  if (!res.ok) throw new Error(await res.text());
}

// ─────────────────────────────────────────────
// 셀 렌더러 — 메뉴명 (인덴트 + 접기/펼치기)
// ─────────────────────────────────────────────
interface MenuNameContext {
  expandedIds: Set<string>;
  toggleExpand: (id: string) => void;
  updateRoles?: (menuId: string, roles: RoleValue[]) => void;
}

function MenuNameRenderer(params: ICellRendererParams) {
  const row = params.data as MenuRowVM;
  const ctx = params.context as MenuNameContext;
  const indent = row.level * 22;
  const isExpanded = ctx.expandedIds.has(row.menuId);

  return (
    <div style={{ display: 'flex', alignItems: 'center', paddingLeft: indent + 4, height: '100%', gap: 6 }}>
      {row.hasChildren ? (
        <span
          onClick={(e) => { e.stopPropagation(); ctx.toggleExpand(row.menuId); }}
          style={{ cursor: 'pointer', userSelect: 'none', fontSize: 10, color: '#f4821f', width: 14, textAlign: 'center', flexShrink: 0, fontWeight: 700 }}
        >
          {isExpanded ? '▾' : '▸'}
        </span>
      ) : (
        <span style={{ width: 14, flexShrink: 0 }} />
      )}
      <span style={{ fontSize: 13, color: row.menuType === 'FOLDER' ? '#f4821f' : '#d1d5db' }}>
        {row.menuType === 'FOLDER' ? '📁 ' : '  '}
        {row.menuName}
      </span>
    </div>
  );
}

function MenuTypeRenderer(p: ICellRendererParams) {
  return p.value === 'FOLDER'
    ? <span style={{ background: 'rgba(244,130,31,0.15)', color: '#f4821f', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600 }}>폴더</span>
    : <span style={{ background: 'rgba(255,255,255,0.06)', color: '#9ca3af', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>프로그램</span>;
}

function UseYnRenderer(p: ICellRendererParams) {
  return p.value === 'Y'
    ? <span style={{ color: '#4ade80', fontWeight: 600 }}>사용</span>
    : <span style={{ color: '#f87171' }}>미사용</span>;
}

// ── 역할 텍스트 렌더러 (레이블 콤마 연결) ────────
function RolesRenderer(p: ICellRendererParams) {
  const roles: RoleValue[] = Array.isArray(p.value) ? p.value : [];
  if (!roles.length) return <span style={{ color: '#4b5563', fontSize: 12 }}>-</span>;
  const text = roles
    .map((rv) => ROLES.find((r) => r.value === rv)?.label ?? rv)
    .join(', ');
  return (
    <span style={{ fontSize: 12, color: '#e5e7eb', lineHeight: '36px' }}>
      {text}
    </span>
  );
}

// ── 역할 멀티선택 팝업 에디터 ──────────────────
const RolesEditor = forwardRef<unknown, ICellEditorParams>((params, ref) => {
  const init = Array.isArray(params.value) ? [...(params.value as RoleValue[])] : [];

  // ref로 동기 보관 → getValue()가 항상 최신 값 반환 (React 렌더 타이밍 무관)
  const selectedRef = useRef<RoleValue[]>(init);
  const [selected, setSelected] = useState<RoleValue[]>(init);

  useImperativeHandle(ref, () => ({
    getValue: () => selectedRef.current,
  }), []);

  const toggle = (rv: RoleValue) => {
    const next = selectedRef.current.includes(rv)
      ? selectedRef.current.filter((x) => x !== rv)
      : [...selectedRef.current, rv];
    selectedRef.current = next;   // 동기 업데이트
    setSelected(next);             // UI 리렌더
  };

  const confirm = () => {
    const menuId = (params.data as MenuRowVM | undefined)?.menuId;
    if (menuId) {
      (params.context as MenuNameContext | undefined)?.updateRoles?.(menuId, [...selectedRef.current]);
    }
    // 커스텀 에디터 값이 커밋되지 않는 케이스를 막기 위해
    // 셀 데이터에 직접 반영 후 편집 종료한다.
    params.node.setDataValue('roles', [...selectedRef.current]);
    params.stopEditing();
  };

  return (
    <div style={{
      background: '#161616', border: '1px solid #f4821f', borderRadius: 8,
      padding: '10px 14px', minWidth: 210, boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div style={{ fontSize: 11, color: '#6b7280', fontWeight: 600, letterSpacing: '0.05em' }}>
        접근 권한 (다중 선택)
      </div>

      {ROLES.map((role) => {
        const checked = selected.includes(role.value);
        return (
          <label key={role.value} style={{
            display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer',
            padding: '6px 10px', borderRadius: 6,
            background: checked ? role.bg : 'transparent',
            border: `1px solid ${checked ? role.color : '#2a2a2a'}`,
            transition: 'all 0.12s',
          }}>
            <input
              type="checkbox"
              checked={checked}
              onChange={() => toggle(role.value)}
              style={{ accentColor: role.color, width: 14, height: 14, cursor: 'pointer' }}
            />
            <span style={{ fontSize: 13, fontWeight: checked ? 700 : 400, color: checked ? role.color : '#9ca3af' }}>
              {role.label}
            </span>
            <span style={{ fontSize: 10, color: '#4b5563', marginLeft: 'auto' }}>({role.value})</span>
          </label>
        );
      })}

      {/* 확인 버튼 — 클릭 시 편집 종료 */}
      <button
        onClick={confirm}
        style={{
          marginTop: 4, padding: '6px 0', borderRadius: 6,
          background: '#f4821f', border: 'none', color: '#fff',
          fontSize: 12, fontWeight: 700, cursor: 'pointer',
        }}
      >
        확인
      </button>
    </div>
  );
});
RolesEditor.displayName = 'RolesEditor';

// ─────────────────────────────────────────────
// 유틸 — 선택 메뉴의 루트까지 경로 빌드
// ─────────────────────────────────────────────
function buildMenuPath(rows: MenuRow[], menuId: string): Array<{ menuId: string; menuName: string; componentKey: string | null }> {
  const path: Array<{ menuId: string; menuName: string; componentKey: string | null }> = [];
  let cur = rows.find((r) => r.menuId === menuId);
  while (cur) {
    path.unshift({ menuId: cur.menuId, menuName: cur.menuName, componentKey: cur.componentKey ?? null });
    if (cur.parentId === ROOT_ID) break;
    cur = rows.find((r) => r.menuId === cur!.parentId);
  }
  return path;
}

// ─────────────────────────────────────────────
// 메인 컴포넌트
// ─────────────────────────────────────────────
const MenuTreeManagement: React.FC = () => {
  // 서버 로드 전 임시로 INITIAL_MENU 사용, 마운트 후 fetchMenuTree로 교체
  const [menuRows, setMenuRows]     = useState<MenuRow[]>(INITIAL_MENU);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    () => new Set(INITIAL_MENU.filter((r) => r.menuType === 'FOLDER').map((r) => r.menuId)),
  );
  const [loading, setLoading] = useState(true);   // 서버 데이터 로딩 중
  const [saving, setSaving]   = useState(false);
  const [toast, setToast]     = useState<string | null>(null);
  const gridApiRef = useRef<GridApi | null>(null);

  // ── 팝업 모드 여부 (opener = Step1AiGenerate) ─
  const isPopup = typeof window !== 'undefined' && !!window.opener;

  // ── 마운트 시 서버에서 메뉴 데이터 로드 ───────
  useEffect(() => {
    fetchMenuTree().then((rows) => {
      if (rows && rows.length > 0) {
        setMenuRows(rows);
        setExpandedIds(new Set(rows.filter((r) => r.menuType === 'FOLDER').map((r) => r.menuId)));
      }
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2500);
    return () => clearTimeout(t);
  }, [toast]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const updateRoles = useCallback((menuId: string, roles: RoleValue[]) => {
    setMenuRows((prev) => prev.map((r) => (r.menuId === menuId ? { ...r, roles } : r)));
  }, []);

  // 가시 행 계산 (expand 상태 반영)
  const rowData = useMemo(
    () => buildVisibleRows(menuRows, expandedIds),
    [menuRows, expandedIds],
  );

  // context: 셀 렌더러에 콜백 전달
  const context = useMemo<MenuNameContext>(
    () => ({ expandedIds, toggleExpand, updateRoles }),
    [expandedIds, toggleExpand, updateRoles],
  );

  const onGridReady = useCallback((e: GridReadyEvent) => {
    gridApiRef.current = e.api;
    e.api.sizeColumnsToFit();
  }, []);

  // ── 드래그 종료 ──────────────────────────────
  const onRowDragEnd = useCallback(
    (event: RowDragEndEvent) => {
      const dragged = event.node.data as MenuRowVM | undefined;
      const over    = event.overNode?.data as MenuRowVM | undefined;
      if (!dragged || !over || dragged.menuId === over.menuId) return;

      if (isDescendant(menuRows, dragged.menuId, over.menuId)) {
        setToast('⚠️ 자기 자신의 하위로 이동할 수 없습니다.');
        return;
      }

      const newParentId = over.menuType === 'FOLDER' ? over.menuId : over.parentId;
      const oldParentId = dragged.parentId;

      const siblings = menuRows
        .filter((r) => r.parentId === newParentId && r.menuId !== dragged.menuId)
        .sort((a, b) => a.sortOrder - b.sortOrder);
      const overIdx  = siblings.findIndex((s) => s.menuId === over.menuId);
      const insertAt = overIdx >= 0 ? overIdx + 1 : siblings.length;

      let next = menuRows.map((r) =>
        r.menuId === dragged.menuId ? { ...r, parentId: newParentId, sortOrder: insertAt + 0.5 } : r,
      );
      next = reorderSiblings(next, oldParentId);
      next = reorderSiblings(next, newParentId);

      // 전체 계층 ID 재생성
      const idMap   = buildIdMap(next);
      const rebuilt = applyIdMap(next, idMap);
      setMenuRows(rebuilt);

      // expandedIds 재매핑 + 이동한 FOLDER는 펼침 유지
      setExpandedIds((ex) => {
        const remapped = new Set([...ex].map((id) => idMap.get(id) ?? id));
        if (dragged.menuType === 'FOLDER') remapped.add(idMap.get(dragged.menuId) ?? dragged.menuId);
        return remapped;
      });
    },
    [menuRows],
  );

  // ── 값 변경 반영: grid 내부 값 -> React 상태 동기화 ─
  const onCellValueChanged = useCallback((e: CellValueChangedEvent<MenuRowVM>) => {
    const row = e.data;
    if (!row) return;
    const normalized = { ...row, roles: normalizeRoles(row.roles) };
    setMenuRows((prev) =>
      prev.map((r) => (r.menuId === normalized.menuId ? { ...r, ...normalized } : r)),
    );
  }, []);

  // ── 저장 (서버 파일에 영구 저장) ────────────
  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const params = normalizeMenuRows([...menuRows].sort((a, b) => a.sortOrder - b.sortOrder));
      await postMenuTree(params);
      setToast('✅ 저장되었습니다. (backend/data/menu_tree.json)');
    } catch {
      setToast('❌ 저장 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  }, [menuRows]);

  // ── 최상위 추가 ───────────────────────────────
  const handleAddRoot = useCallback(() => {
    setMenuRows((prev) => {
      const count = prev.filter((r) => r.parentId === ROOT_ID).length;
      const so    = count + 1;
      const newId = `ROOT${String(so).padStart(2, '0')}`;
      const newRow: MenuRow = {
        menuId: newId,
        menuName: '새 최상위 메뉴',
        parentId: ROOT_ID,
        sortOrder: so,
        menuType: 'FOLDER',
        useYn: 'Y',
        roles: [],
      };
      setExpandedIds((ex) => new Set([...ex, newId]));
      return [...prev, newRow];
    });
  }, []);

  // ── 하위 추가 ─────────────────────────────────
  const handleAddChild = useCallback(() => {
    const selected = gridApiRef.current?.getSelectedNodes() ?? [];
    if (!selected.length) { setToast('⚠️ 먼저 FOLDER 메뉴를 선택하세요.'); return; }
    const parent = selected[0].data as MenuRowVM;
    if (parent.menuType !== 'FOLDER') { setToast('⚠️ FOLDER 타입에만 하위를 추가할 수 있습니다.'); return; }

    setMenuRows((prev) => {
      const count = prev.filter((r) => r.parentId === parent.menuId).length;
      const newId = `${parent.menuId}${String(count + 1).padStart(2, '0')}`;
      setExpandedIds((ex) => new Set([...ex, parent.menuId]));
      return [
        ...prev,
        {
          menuId: newId,
          menuName: '새 메뉴',
          parentId: parent.menuId,
          sortOrder: count + 1,
          menuType: 'PROGRAM',
          useYn: 'Y',
          roles: [],
        },
      ];
    });
  }, []);

  // ── 삭제 ─────────────────────────────────────
  const handleDelete = useCallback(() => {
    const selected = gridApiRef.current?.getSelectedNodes() ?? [];
    if (!selected.length) { setToast('⚠️ 삭제할 항목을 선택하세요.'); return; }
    const targetIds = new Set(selected.map((n) => (n.data as MenuRowVM).menuId));

    const toDelete = new Set<string>();
    function mark(id: string) {
      toDelete.add(id);
      menuRows.filter((r) => r.parentId === id).forEach((c) => mark(c.menuId));
    }
    targetIds.forEach((id) => mark(id));

    const filtered = menuRows.filter((r) => !toDelete.has(r.menuId));
    const idMap    = buildIdMap(filtered);
    setMenuRows(applyIdMap(filtered, idMap));
    setExpandedIds((ex) => new Set([...ex].map((id) => idMap.get(id) ?? id).filter((id) => !toDelete.has(id))));
  }, [menuRows]);

  // ── 초기화 (서버 파일도 INITIAL_MENU로 덮어씀) ─
  const handleReset = useCallback(() => {
    if (!window.confirm('초기 데이터로 복원하시겠습니까?\n서버에 저장된 메뉴 정보도 초기화됩니다.')) return;
    setMenuRows(INITIAL_MENU);
    setExpandedIds(new Set(INITIAL_MENU.filter((r) => r.menuType === 'FOLDER').map((r) => r.menuId)));
    postMenuTree(INITIAL_MENU).catch(() => {/* 초기화 실패는 무시 */});
  }, []);

  // ── 전체 펼치기 / 접기 ────────────────────────
  const handleExpandAll  = useCallback(() =>
    setExpandedIds(new Set(menuRows.filter((r) => r.menuType === 'FOLDER').map((r) => r.menuId))), [menuRows]);
  const handleCollapseAll = useCallback(() => setExpandedIds(new Set()), []);

  // ── AI 병합 확장 공간 ─────────────────────────
  const loadAiSuggestedMenu = useCallback((_ai: MenuRow[]) => {
    setMenuRows((prev) => {
      const existIds = new Set(prev.map((r) => r.menuId));
      const toAdd = _ai.filter((m) => !existIds.has(m.menuId));
      if (!toAdd.length) return prev;
      const merged = [...prev, ...toAdd];
      const idMap  = buildIdMap(merged);
      return applyIdMap(merged, idMap);
    });
  }, []);
  void loadAiSuggestedMenu;

  // ── 팝업 모드: 선택 완료 → opener에 경로 전송 ─
  const handleSelectConfirm = useCallback(() => {
    const selected = gridApiRef.current?.getSelectedNodes() ?? [];
    if (!selected.length) {
      setToast('⚠️ 메뉴를 먼저 선택하세요.');
      return;
    }
    const row = selected[0].data as MenuRowVM;
    const path = buildMenuPath(menuRows, row.menuId);
    window.opener?.postMessage({ type: 'MENU_SELECTED', path }, '*');
    window.close();
  }, [menuRows]);

  // ── 컬럼 정의 ─────────────────────────────────
  const columnDefs = useMemo<ColDef<MenuRowVM>[]>(() => [
    {
      colId: 'drag',
      headerName: '',
      width: 42,
      maxWidth: 42,
      rowDrag: true,
      suppressSizeToFit: true,
      sortable: false,
      resizable: false,
      cellRenderer: () => (
        <span style={{ cursor: 'grab', color: '#9ca3af', fontSize: 16, lineHeight: '36px' }}>⠿</span>
      ),
    },
    {
      field: 'menuName',
      headerName: '메뉴명',
      flex: 2,
      minWidth: 200,
      editable: true,
      cellRenderer: MenuNameRenderer,
    },
    {
      field: 'menuId',
      headerName: '메뉴 ID',
      width: 130,
      editable: false,
    },
    {
      field: 'menuType',
      headerName: '유형',
      width: 110,
      editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: ['FOLDER', 'PROGRAM'] },
      cellRenderer: MenuTypeRenderer,
    },
    {
      field: 'componentKey',
      headerName: '컴포넌트키',
      width: 140,
      editable: true,
      valueFormatter: (p) => (p.value as string | null | undefined) ?? '-',
    },
    {
      field: 'roles',
      headerName: '접근권한',
      flex: 1,
      minWidth: 190,
      editable: true,
      cellDataType: 'object',           // warning #48 억제
      cellRenderer: RolesRenderer,
      cellEditor: RolesEditor,
      cellEditorPopup: true,
      cellEditorPopupPosition: 'under',
      valueSetter: (p) => {
        const next = Array.isArray(p.newValue) ? p.newValue as RoleValue[] : [];
        p.data.roles = next;
        return true;
      },
      valueParser: (p) => p.newValue,   // 배열 그대로 반환
      valueFormatter: () => '',         // 텍스트 fallback 없음 (렌더러가 처리)
    },
    {
      field: 'useYn',
      headerName: '사용여부',
      width: 95,
      editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: ['Y', 'N'] },
      cellRenderer: UseYnRenderer,
    },
    {
      field: 'sortOrder',
      headerName: '순서',
      width: 65,
      editable: false,
    },
  ], []);

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: false,
    resizable: true,
  }), []);

  const BTN_BASE: React.CSSProperties = {
    padding: '6px 13px', fontSize: 12, borderRadius: 6,
    border: '1px solid #333', cursor: 'pointer', fontWeight: 600,
    background: '#1f1f1f', color: '#d1d5db', transition: 'background 0.15s',
  };
  const BTN_ORANGE: React.CSSProperties = {
    ...BTN_BASE, background: '#f4821f', border: '1px solid #f4821f', color: '#fff',
  };
  const BTN_GHOST: React.CSSProperties = {
    ...BTN_BASE, background: 'transparent', color: '#6b7280',
  };

  return (
    <>
      <style>{EXTRA_CSS}</style>

      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'system-ui, sans-serif', background: '#0f0f0f', color: '#f9fafb' }}>

        {/* 헤더 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 20px', background: '#111111', borderBottom: '1px solid #2a2a2a' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ color: '#f4821f', fontSize: 18 }}>☰</span>
            <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f9fafb' }}>메뉴 트리 관리</h1>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            <button onClick={handleExpandAll}   style={BTN_BASE}>전체 펼치기</button>
            <button onClick={handleCollapseAll} style={BTN_BASE}>전체 접기</button>
            <div style={{ width: 1, height: 20, background: '#2a2a2a' }} />
            <button onClick={handleAddRoot}  style={BTN_BASE}>+ 최상위</button>
            <button onClick={handleAddChild} style={BTN_BASE}>+ 하위</button>
            <button onClick={handleDelete}   style={{ ...BTN_BASE, color: '#f87171', border: '1px solid #3a1a1a' }}>삭제</button>
            <button onClick={handleReset}    style={BTN_GHOST}>초기화</button>
            <div style={{ width: 1, height: 20, background: '#2a2a2a' }} />
            {/* 팝업 모드일 때만 "선택 완료" 표시, 일반 모드는 "저장" 표시 */}
            {isPopup ? (
              <button onClick={handleSelectConfirm}
                style={{ ...BTN_ORANGE, padding: '6px 18px', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 14 }}>✓</span> 선택 완료
              </button>
            ) : (
              <button onClick={handleSave} disabled={saving}
                style={{ ...BTN_ORANGE, opacity: saving ? 0.5 : 1, cursor: saving ? 'not-allowed' : 'pointer', padding: '6px 18px' }}>
                {saving ? '저장 중…' : '저장'}
              </button>
            )}
          </div>
        </div>

        {/* 안내 */}
        <div style={{ padding: '5px 20px', fontSize: 11, color: '#4b5563', background: '#0f0f0f', borderBottom: '1px solid #1a1a1a' }}>
          {isPopup
            ? '📌 메뉴를 클릭하여 선택한 뒤 [선택 완료] 버튼을 누르세요.'
            : '⠿ 드래그로 순서·계층 변경 | ▸ 클릭으로 접기/펼치기 | 셀 더블클릭으로 편집'}
        </div>

        {/* 그리드 */}
        <div className="ag-menu-wrap" style={{ flex: 1, padding: '12px 16px', minHeight: 0, position: 'relative' }}>
          {loading && (
            <div style={{
              position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(0,0,0,0.5)', zIndex: 10, borderRadius: 8, fontSize: 13, color: '#9ca3af',
            }}>
              ⏳ 메뉴 데이터 불러오는 중…
            </div>
          )}
          <div style={{ height: '100%', width: '100%', borderRadius: 8, overflow: 'hidden', border: '1px solid #2a2a2a' }}>
            <AgGridReact<MenuRowVM>
              theme={darkTheme}
              rowData={rowData}
              columnDefs={columnDefs}
              defaultColDef={defaultColDef}
              context={context}
              rowDragManaged={false}
              onRowDragEnd={onRowDragEnd}
              rowSelection={{ mode: 'singleRow' }}
              onGridReady={onGridReady}
              onCellValueChanged={onCellValueChanged}
              rowHeight={36}
              headerHeight={38}
              animateRows={true}
              getRowId={(p) => p.data.menuId}
            />
          </div>
        </div>

        {/* 토스트 */}
        {toast && (
          <div style={{
            position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
            padding: '10px 22px', background: '#1a1a1a', color: '#f9fafb',
            border: '1px solid #f4821f', borderRadius: 8,
            fontSize: 13, boxShadow: '0 4px 20px rgba(244,130,31,0.2)', zIndex: 9999,
          }}>
            {toast}
          </div>
        )}
      </div>
    </>
  );
};

export default MenuTreeManagement;
