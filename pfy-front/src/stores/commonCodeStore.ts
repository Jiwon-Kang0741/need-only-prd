import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

import {
  type CodeDict,
  type CommonCodeItem,
  fetchCodeComboMulti,
  type FetchCodeComboParams,
  fetchCommonCodes,
} from '@/api/commonCodes';
import i18n from '@/plugins/i18n';

export interface LoadMultiItem {
  id: string; // 저장 키 (Code는 clsId, Query는 사용자 정의 키)
  queryId?: string; // Query 타입 전용: 실제 쿼리 ID (예: "BMCM010.ContCombo")
  clsId?: string; // Code 타입 전용: 공통코드 그룹 ID (예: "COM_CLS_0000")
  whereClause?: string | Record<string, any>; // Query 타입 전용: WHERE 조건 (문자열: "pblCd=A001;deptCds=D01,D02,D03" 또는 객체: { pblCd: 'A001', deptCds: ['D01', 'D02', 'D03'] })
  useYn?: 'Y' | 'N' | 'ALL'; // Code 타입 전용: 사용여부 (기본: 'Y')
  reloadYn?: 'N' | 'Y'; // 재로드 여부 (기본: 'N')
}

export const useCommonCodeStore = defineStore(
  'commonCode',
  () => {
    const dict = ref<CodeDict>({}); // Code/Query 타입 통합 저장소
    const loading = ref(false);
    const error = ref<string | null>(null);

    /**
     * LoadMultiItem으로 타입 추론
     * - queryId가 있으면 Query 타입
     * - queryId가 없고 id에 점(.)이 있으면 Query 타입 (하위 호환)
     * - 그 외는 Code 타입
     */
    function inferType(item: LoadMultiItem): 'Query' | 'Code' {
      if (item.queryId) return 'Query';
      return 'Code';
    }

    /** 공통코드 로드 (여러 clsId 한번에) */
    async function load(
      clsIds: string[],
      useYn?: 'Y' | 'N' | 'ALL',
      codeCtrlN2?: string,
      codeCtrlN1s?: string[]
    ) {
      if (!clsIds?.length) return;
      loading.value = true;
      error.value = null;
      try {
        const res = await fetchCommonCodes({
          clsIds,
          useYn,
          codeCtrlN2,
          codeCtrlN1s,
        });
        dict.value = { ...dict.value, ...res };
      } catch (e: any) {
        error.value = e?.message ?? 'Failed to load common codes';
      } finally {
        loading.value = false;
      }
    }

    /** 필요한 clsId가 캐시에 없으면 로드 */
    async function ensureLoaded(
      ids: string[] | string,
      useYn?: 'Y' | 'N' | 'ALL',
      codeCtrlN2?: string,
      codeCtrlN1s?: string[]
    ) {
      const list = Array.isArray(ids) ? ids : [ids];
      const missing = list.filter(
        (id) => !dict.value[id] || dict.value[id].length === 0
      );
      if (missing.length) await load(missing, useYn, codeCtrlN2, codeCtrlN1s);
    }

    /**
     * 여러 데이터를 한번에 로드 (Query 또는 Code 타입)
     * - 백엔드에서 queryId/clsId 유무로 타입 판단
     * - 로컬에 이미 있으면 스킵
     */
    async function loadMulti(items: LoadMultiItem[]) {
      if (!items?.length) return;

      loading.value = true;
      error.value = null;

      try {
        // 로컬에 없는 것만 필터링
        const itemsToLoad = items.filter((item) => {
          return !dict.value[item.id] || dict.value[item.id].length === 0;
        });

        if (!itemsToLoad.length) {
          loading.value = false;
          return;
        }

        // 모든 항목을 하나의 요청으로 변환
        const requestList: FetchCodeComboParams[] = itemsToLoad.map((item) => {
          const type = inferType(item);

          if (type === 'Query') {
            // Query 타입: queryId와 whereClause를 문자열 그대로 전달
            const request: FetchCodeComboParams = {
              id: item.id,
              queryId: item.queryId,
            };

            // whereClause가 있으면 문자열 또는 객체 그대로 전달
            if (item.whereClause) {
              if (typeof item.whereClause === 'string') {
                request.whereClause = item.whereClause;
              } else {
                // 객체인 경우 문자열로 변환하여 전달
                const parts: string[] = [];
                Object.entries(item.whereClause).forEach(([key, value]) => {
                  if (Array.isArray(value)) {
                    parts.push(`${key}=${value.join(',')}`);
                  } else {
                    parts.push(`${key}=${value}`);
                  }
                });
                request.whereClause = parts.join(';');
              }
            }

            return request;
          }

          // Code 타입: clsId 전달
          return {
            id: item.id,
            clsId: item.clsId ?? item.id,
            useYn: item.useYn ?? 'Y',
          };
        });

        // 백엔드에 일괄 요청
        const res = await fetchCodeComboMulti(requestList);

        // load 함수처럼 기존 dict에 병합
        dict.value = { ...dict.value, ...res };
      } catch (e: any) {
        error.value = e?.message ?? 'Failed to load multi codes';
        throw e;
      } finally {
        loading.value = false;
      }
    }

    /** 필요한 ID들이 캐시에 없으면 로드 (Query 또는 Code 타입) */
    async function ensureLoadedMulti(items: LoadMultiItem[]) {
      if (!items?.length) return;

      // reloadYn이 'Y'인 항목들 제거
      const reloadItems = items.filter((item) => item.reloadYn === 'Y');
      reloadItems.forEach((item) => {
        dict.value[item.id] = [];
      });

      // 로컬에 없는 것만 필터링
      const missing = items.filter((item) => {
        return !dict.value[item.id] || dict.value[item.id].length === 0;
      });

      // 캐시에 모두 있으면 바로 리턴
      if (!missing.length) return;

      // 없는 것만 loadMulti로 로드
      await loadMulti(missing);
    }

    /** 로그인 직후 초기로딩 */
    async function initOnLogin() {
      await load([
        'COM_CLS_0000',
        'COM_CLS_0001',
        'COM_BIZ_0000',
        'COM_BIZ_0001',
        'COM_BIZ_0003',
        'COM_BIZ_0007',
        'COM_BIZ_0008',
        // 'COM_BIZ_0009',
        // 'COM_CLS_0076', // SPS에서는 0004가 useYn 이었음
      ]);
    }

    /** 원본 배열 (Code 타입 전용) */
    function raw(clsId: string): CommonCodeItem[] {
      return dict.value[clsId] || [];
    }

    /**
     * ID가 캐시에 있는지 확인 (Code/Query 타입 모두 지원)
     * @param id - 저장 키 (Code ID 또는 Query의 사용자 정의 id)
     */
    function validateId(id: string): boolean {
      const list = dict.value[id];
      return list && list.length > 0;
    }

    /**
     * Code ID가 캐시에 있는지 확인 (하위 호환성 유지)
     * @deprecated validateId() 사용 권장
     */
    function validateClsId(clsId: string): boolean {
      // 현재 스토어에 해당 clsId가 있는지 확인
      const list = raw(clsId);
      return list && list.length > 0;
    }

    /**
     * 셀렉트 옵션: 라벨=codeNm, 값=codeCd
     * - Code 타입: id로 dict에서 조회
     * - Query 타입: id로 dict에서 조회
     */
    function options(
      id: string,
      includeAll = false,
      allLabel: string = 'ALL', // 라벨 기본값
      allValue: string = 'ALL', // 값 기본값 ('ALL' / '' 가능)
      customParam?: string | Record<string, any> // KEY=VALUE;KEY=VALUE 형식 또는 객체로 필터링
    ) {
      // ✅ id로 직접 조회 (Code든 Query든 동일)
      if (!validateId(id)) {
        return null;
      }

      let list = [...(dict.value[id] || [])];

      // customParam으로 필터링 (KEY=VALUE;KEY=VALUE 형식)
      // 값에 쉼표가 있으면 OR 조건: KEY=VALUE1,VALUE2 -> KEY가 VALUE1 또는 VALUE2
      if (customParam) {
        try {
          let filterObj: Record<string, any>;

          if (typeof customParam === 'string') {
            // "KEY_A=VALUE_A;KEY_B=VALUE_B" 형식 파싱
            filterObj = {};
            const pairs = customParam.split(';').filter((s) => s.trim());
            pairs.forEach((pair) => {
              const [key, value] = pair.split('=').map((s) => s.trim());
              if (key && value !== undefined) {
                filterObj[key] = value;
              }
            });
          } else {
            // 이미 객체인 경우 그대로 사용
            filterObj = customParam;
          }

          list = list.filter((item) => {
            // 모든 조건을 만족해야 함 (AND 조건)
            return Object.entries(filterObj).every(([key, value]) => {
              // 소문자로 변환하여 비교 (대소문자 구분 없음)
              const itemKey = Object.keys(item).find(
                (k) => k.toLowerCase() === key.toLowerCase()
              );
              if (!itemKey) return false;

              const itemValue = String(item[itemKey]);
              const filterValue = String(value);

              // 값에 쉼표가 있으면 OR 조건 (VALUE1,VALUE2,VALUE3)
              if (filterValue.includes(',')) {
                const values = filterValue.split(',').map((v) => v.trim());
                return values.some((v) => itemValue === v);
              }

              // 단일 값이면 일치 비교
              return itemValue === filterValue;
            });
          });
        } catch (e) {
          console.error('Failed to parse customParam:', customParam, e);
          // 파싱 실패 시 필터링하지 않음
        }
      }

      list.sort((a, b) => {
        const sa = Number(a.codeSort ?? 0);
        const sb = Number(b.codeSort ?? 0);
        if (sa !== sb) return sa - sb;
        return (a.codeNm ?? '').localeCompare(b.codeNm ?? '');
      });

      const opts = list.map((it) => ({
        name: (it.codeNm ?? '').replace(/<br\s*\/?>(\s*)?/gi, ' / '),
        value: it.codeCd,
        raw: it,
      }));

      if (includeAll) {
        opts.unshift({
          name: allLabel, // ALL
          value: allValue, // '' | 'ALL'  선택 가능
          raw: null as any,
        });
      }

      return opts;
    }

    /** 태그/상태 맵: { 코드: {label, severity?, raw} } */
    function codeMap(
      clsId: string,
      severityByCode: Record<string, string> = {}
    ) {
      const map: Record<
        string,
        {
          label: string;
          severity?: string;
          status?: string;
          raw: CommonCodeItem;
        }
      > = {};
      raw(clsId).forEach((it) => {
        const code = it.codeCd;
        const level = severityByCode[code] ?? it.codeCtrlN2; // codeCtrlN2에 넣어주면 자동 반영
        map[code] = {
          label: (it.codeNm ?? '').replace(/<br\s*\/?>(\s*)?/gi, ' / '),
          severity: level,
          status: level,
          raw: it,
        };
      });
      return map;
    }

    /** 전역 캐시 초기화(로그아웃 등) */
    function reset() {
      dict.value = {};
      error.value = null;
    }

    async function refreshLoaded() {
      const ids = Object.keys(dict.value);
      if (ids.length) await load(ids, 'Y');
    }

    /** 셀렉트 옵션 라벨 조회 */
    function getOptionName(clsId: string, value: string) {
      if (!validateClsId(clsId)) {
        return value;
      }

      const targetOptions = options(clsId, true);
      const targetOption = targetOptions?.find(
        (option: any) => option.value === value
      );
      return targetOption?.name || value;
    }

    /** 셀렉트 옵션 값 조회 */
    function getOptionValue(clsId: string, label: string) {
      if (!validateClsId(clsId)) {
        return label;
      }

      const targetOptions = options(clsId, true);
      const targetOption = targetOptions?.find(
        (option: any) => option.name === label
      );
      return targetOption?.value || label;
    }

    /** 셀렉트 필터 * */

    /** clsId + 여러 codeCd 배열로 옵션들 반환 */
    /** 사용 예시 commonCodeStore.optionByCodes('COM_BIZ_0016', ['A1', 'A2', 'B1', 'B2']) * */
    function optionByCodes(clsId: string, codeCds: string[]) {
      const list = raw(clsId);
      const targets = list.filter((item) => codeCds.includes(item.codeCd));
      return targets.map((it) => ({
        name: it.codeNm ?? it.codeCd,
        value: it.codeCd,
        raw: it,
      }));
    }

    /**
     * clsId + windowId 조합으로 옵션 반환
     * 하나의 옵션 목록으로 페이지마다 다르게 보여주고 싶을때 windowId를 사용하여 필요한 옵션을 반환
     * 예) 수리부속 기간 조건(진행현황, 구매통계, 접수, 인보이스 페이지마다 다름)
     * @param clsId 그룹코드
     * @param windowId 호출하는 페이지 Id - 공통코드관리의 코드제어 01과 매핑
     */
    async function optionByWindowId(clsId: string[], windowId: string[]) {
      await load(clsId, 'Y', '', windowId);
    }

    watch(
      () => i18n.global.locale.value,
      async () => {
        try {
          await refreshLoaded();
        } catch (e) {
          console.error(e);
        }
      },
      { flush: 'sync' }
    );

    return {
      dict,
      loading,
      error,
      load,
      loadMulti,
      ensureLoaded,
      ensureLoadedMulti,
      initOnLogin,
      raw,
      validateId,
      validateClsId,
      options,
      optionByCodes,
      getOptionName,
      getOptionValue,
      codeMap,
      reset,
      optionByWindowId,
    };
  },
  {
    persist: {
      storage: sessionStorage,
    },
  }
);
