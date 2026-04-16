import { computed, nextTick, reactive, watchEffect } from 'vue';

export function useTableFilter(props: any, emit: any, popoverRefs: any) {
  const filters = reactive<Record<string, { value: any; matchMode: string }>>(
    {}
  );
  const selectedFilterValues = reactive<Record<string, any[]>>({});
  const searchText = reactive<Record<string, string>>({});

  const fields = computed(() => (props.columns ?? []).map((c: any) => c.field));
  const getCol = (field: string) =>
    (props.columns ?? []).find((c: any) => c.field === field);

  // ------- DOM 라벨 캐시 (field -> Map<raw, label>) -------
  const domLabelCache: Record<string, Map<any, string>> = {};

  const cleanText = (s: string | null | undefined) =>
    (s ?? '')
      .replace(/\s+/g, ' ')
      .replace(/\u00A0/g, ' ')
      .trim();

  // 비교용 정규화(공백/구분자 제거 + 소문자 + NFKC)
  const normalize = (s: string | null | undefined) =>
    cleanText(s)
      .toLowerCase()
      .normalize('NFKC')
      .replace(/[\s\u00A0·•.,/()\-_[\]{}]+/g, '');

  // 테이블 DOM에서 표시 라벨을 raw와 매칭
  const syncDomLabels = async (field: string) => {
    await nextTick();
    try {
      const rows: any[] = Array.isArray(props.value) ? props.value : [];
      if (!rows.length) return;

      const nodes = Array.from(
        document.querySelectorAll<HTMLElement>(
          `.p-datatable .p-datatable-tbody [data-p-field="${field}"]`
        )
      );
      if (!nodes.length) return;

      const map = domLabelCache[field] ?? new Map<any, string>();
      const len = Math.min(nodes.length, rows.length);

      nodes.slice(0, len).forEach((node, i) => {
        const raw = rows[i]?.[field];
        if (raw == null) return;
        const label = cleanText(node?.textContent ?? '');
        if (label) map.set(raw, label);
      });

      if (!domLabelCache[field]) domLabelCache[field] = map;
    } catch {
      //
    }
  };

  const findFromArrayOptions = (col: any, raw: any) => {
    const buckets = [
      col?.options,
      col?.optionList,
      col?.dict,
      col?.codeList,
    ].filter(Boolean);
    const hit =
      buckets.reduce((acc: any, list: any) => {
        if (acc) return acc;
        if (!Array.isArray(list)) return null;
        return (
          list.find((it: any) => it?.value === raw || it?.codeCd === raw) ??
          null
        );
      }, null) ?? null;

    if (!hit) return null;
    const text =
      hit?.label ??
      hit?.name ??
      hit?.codeNm ??
      hit?.codeNmKor ??
      hit?.codeCd ??
      raw;
    return String(text);
  };

  const findFromObjectMap = (col: any, raw: any) => {
    const map = col?.map;
    if (map && Object.prototype.hasOwnProperty.call(map, raw)) {
      const v = map[raw];
      if (v == null) return null;
      if (typeof v === 'string' || typeof v === 'number') return String(v);
      const lbl = v?.label ?? v?.name ?? v?.codeNm ?? v?.codeNmKor;
      if (lbl != null) return String(lbl);
    }
    return null;
  };

  const findFromRowLabelFields = (field: string, row: any) => {
    const keys = [`${field}Label`, `${field}Nm`, `${field}Name`, `${field}Txt`];
    const k = keys.find((kk) => row?.[kk] != null && row?.[kk] !== '');
    return k ? String(row[k]) : null;
  };

  const tryFormatDate = (field: any, raw: any) => {
    if (raw == null) return null;

    const parseToDate = (v: any) => {
      if (v instanceof Date) return v;
      if (typeof v !== 'string') return null;

      const looksLikeDate =
        /\d{4}-\d{2}-\d{2}/.test(v) ||
        /\d{4}[./-]\s*\d{1,2}[./-]\s*\d{1,2}\.?/.test(v) ||
        field.endsWith('Dt') ||
        field.endsWith('Dtm');

      if (!looksLikeDate) return null;

      const d = new Date(v);
      return Number.isNaN(d.getTime()) ? null : d;
    };

    const date = parseToDate(raw);
    if (!date) return null;

    const locale =
      navigator.language || document.documentElement.lang || 'en-US';
    try {
      return new Intl.DateTimeFormat(locale, {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
      }).format(date);
    } catch {
      return date.toLocaleDateString();
    }
  };

  const getDisplayText = async (
    field: string,
    rawValue: any,
    row?: any
  ): Promise<string> => {
    const col = getCol(field);

    const byOptions = col ? findFromArrayOptions(col, rawValue) : null;
    if (byOptions != null) return byOptions;

    const byMap = col ? findFromObjectMap(col, rawValue) : null;
    if (byMap != null) return byMap;

    if (col?.display) {
      const v = col.display(rawValue, row);
      if (v != null && v !== '') return String(v);
    }

    if (row) {
      const byRow = findFromRowLabelFields(field, row);
      if (byRow != null) return byRow;
    }

    const byDate = tryFormatDate(field, rawValue);
    if (byDate != null) return byDate;

    const cached = domLabelCache[field]?.get(rawValue);
    if (cached) return cached;

    await syncDomLabels(field);
    const afterSync = domLabelCache[field]?.get(rawValue);
    if (afterSync) return afterSync;

    return String(rawValue ?? '');
  };

  // 필터 옵션 맵 (name=라벨, value=raw)
  const filterOptionsMap = computed(() => {
    const result: Record<string, Array<{ name: string; value: any }>> = {};
    (props.columns ?? []).forEach((col: any) => {
      const uniqRaw = Array.from(
        new Set(
          (props.value ?? [])
            .map((row: any) => row?.[col.field])
            .filter((v: any) => v != null)
        )
      );

      // 초기에는 raw로 채우고, resolveLabels에서 라벨 덮어쓰기
      result[col.field] = uniqRaw.map((raw: any) => ({
        name: String(raw),
        value: raw,
      }));
      nextTick().then(() => syncDomLabels(col.field));
    });
    return result;
  });

  // 라벨 갱신
  const resolveLabels = async (field: any) => {
    const list = filterOptionsMap.value[field] ?? [];
    const rows = Array.isArray(props.value) ? props.value : [];

    const updated = await Promise.all(
      list.map(async (it) => {
        const raw = it.value;
        const sampleRow = rows.find((r: any) => r?.[field] === raw);
        const name = await getDisplayText(field, raw, sampleRow);
        return { ...it, name };
      })
    );

    updated.forEach((it, idx) => {
      list.splice(idx, 1, it); // 참조 유지
    });
  };

  // 렌더/데이터 변경 시 라벨 보정
  watchEffect(() => {
    (props.columns ?? []).forEach((col: any) => {
      const p = resolveLabels(col.field);
      if (p && typeof p.then === 'function') p.then(() => {});
    });
  });

  /**
   *  실시간 입력: 라벨 기준 역매핑 → in 필터로 즉시 적용
   */
  const handleFilterInput = async (
    field: string,
    e: Event,
    callback: (val: any) => void
  ) => {
    const target = e.target as HTMLInputElement | null;
    if (!target) return;

    const keyword = target.value ?? '';
    searchText[field] = keyword;

    const kw = keyword.trim();
    if (kw === '') {
      // 키워드 없으면 contains 초기화
      filters[field] = { value: null, matchMode: 'contains' };
      selectedFilterValues[field] = [];
      callback(null);
      return;
    }

    const kwNorm = normalize(kw);
    const matches = new Set<any>();

    // 최신 라벨 확보
    await resolveLabels(field);

    // 1) 옵션 라벨에서 역매핑
    const opts = filterOptionsMap.value[field] ?? [];
    opts.forEach((opt) => {
      if (normalize(opt.name).includes(kwNorm)) {
        matches.add(opt.value);
      }
    });

    // 2) 보조 소스 (DOM/행라벨/날짜/RAW)
    await syncDomLabels(field);
    const rows: any[] = Array.isArray(props.value) ? props.value : [];
    rows.forEach((row) => {
      const raw = row?.[field];
      if (raw == null) return;

      const cacheLbl = domLabelCache[field]?.get(raw);
      if (cacheLbl && normalize(cacheLbl).includes(kwNorm)) {
        matches.add(raw);
        return;
      }

      const byRow = findFromRowLabelFields(field, row);
      if (byRow && normalize(byRow).includes(kwNorm)) {
        matches.add(raw);
        return;
      }

      const byDate = tryFormatDate(field, raw);
      if (byDate && normalize(byDate).includes(kwNorm)) {
        matches.add(raw);
        return;
      }

      if (normalize(String(raw)).includes(kwNorm)) {
        matches.add(raw);
      }
    });

    const vals = Array.from(matches);
    selectedFilterValues[field] = vals;

    // 실시간 in 필터 적용
    filters[field] = { value: vals, matchMode: 'in' };
    callback(vals);
  };

  // 필터 전체 선택 여부 확인
  const isFilterAllSelected = (field: string) => {
    const options =
      filterOptionsMap.value[field]?.map((o: any) => o.value) ?? [];
    const selected = selectedFilterValues[field] ?? [];
    return (
      options.length > 0 && options.every((v: any) => selected.includes(v))
    );
  };

  // 필터 전체 선택/해제 (실제 적용은 '설정')
  const toggleAll = (field: string, callback?: (val: any) => void) => {
    const allValues =
      filterOptionsMap.value[field]?.map((o: any) => o.value) ?? [];
    selectedFilterValues[field] = isFilterAllSelected(field)
      ? []
      : [...allValues];
    filters[field] = { value: selectedFilterValues[field], matchMode: 'in' };
    callback?.(filters[field].value);
  };

  // 필터 취소
  const cancelFilter = (field: string, callback?: (val: any) => void) => {
    selectedFilterValues[field] = [];
    searchText[field] = '';
    filters[field] = { value: null, matchMode: 'contains' };
    callback?.(null);
    popoverRefs[field]?.hide();
  };

  // 필터 적용 (체크박스/키워드 → in)
  const applyFilter = async (field: string, callback?: (val: any) => void) => {
    let vals = selectedFilterValues[field] ?? [];

    const kw = (searchText[field] ?? '').trim();
    if ((!vals || vals.length === 0) && kw !== '') {
      const kwNorm = normalize(kw);
      const matches = new Set<any>();

      await resolveLabels(field);

      const opts = filterOptionsMap.value[field] ?? [];
      opts.forEach((opt) => {
        if (normalize(opt.name).includes(kwNorm)) {
          matches.add(opt.value);
        }
      });

      await syncDomLabels(field);
      const rows: any[] = Array.isArray(props.value) ? props.value : [];
      rows.forEach((row) => {
        const raw = row?.[field];
        if (raw == null) return;

        const cacheLbl = domLabelCache[field]?.get(raw);
        if (cacheLbl && normalize(cacheLbl).includes(kwNorm)) {
          matches.add(raw);
          return;
        }

        const byRow = findFromRowLabelFields(field, row);
        if (byRow && normalize(byRow).includes(kwNorm)) {
          matches.add(raw);
          return;
        }

        const byDate = tryFormatDate(field, raw);
        if (byDate && normalize(byDate).includes(kwNorm)) {
          matches.add(raw);
          return;
        }

        if (normalize(String(raw)).includes(kwNorm)) {
          matches.add(raw);
        }
      });

      vals = Array.from(matches);
      selectedFilterValues[field] = vals;
    }

    filters[field] = { value: vals, matchMode: 'in' };
    callback?.(filters[field].value);

    // 표시용 라벨 업데이트
    await resolveLabels(field);

    filters[field] = { value: vals, matchMode: 'in' };
    callback?.(filters[field].value);
    popoverRefs[field]?.hide();
  };

  // 기본값 선세팅
  watchEffect(() => {
    fields.value.forEach((key: string) => {
      if (!filters[key]) filters[key] = { value: null, matchMode: 'contains' };
      if (!selectedFilterValues[key]) selectedFilterValues[key] = [];
      if (searchText[key] == null) searchText[key] = '';
    });
  });

  // 필터 초기화
  const resetFilters = () => {
    fields.value.forEach((key: string) => {
      filters[key] = { value: null, matchMode: 'contains' };
      selectedFilterValues[key] = [];
      searchText[key] = '';
    });
  };

  return {
    filters,
    selectedFilterValues,
    filterOptionsMap,
    handleFilterInput,
    isFilterAllSelected,
    toggleAll,
    cancelFilter,
    applyFilter,
    resetFilters,
    searchText,
  };
}
