import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/plugins/axios'

interface CodeOption {
  label: string
  value: string
  [key: string]: unknown
}

export const useCommonCodeStore = defineStore('commonCode', () => {
  const cache = ref<Record<string, CodeOption[]>>({})
  const loading = ref<Record<string, boolean>>({})

  async function loadMulti(queries: { QueryId: string; [key: string]: unknown }[]) {
    for (const q of queries) {
      if (cache.value[q.QueryId]) continue // Already loaded
      loading.value[q.QueryId] = true
      try {
        // Try to fetch from backend common code API
        const response = await api.post('/online/mvcJson/BMCM010/selectCommonCode', {
          QUERY_ID: q.QueryId,
        })
        const payload = response.data?.payload
        if (Array.isArray(payload)) {
          cache.value[q.QueryId] = payload.map((item: Record<string, unknown>) => ({
            label: String(item.CODE_NM || item.label || item.name || ''),
            value: String(item.CODE || item.value || item.code || ''),
            ...item,
          }))
        } else {
          cache.value[q.QueryId] = []
        }
      } catch {
        // Graceful fallback: empty options
        cache.value[q.QueryId] = []
      } finally {
        loading.value[q.QueryId] = false
      }
    }
  }

  function options(queryId: string, addAll?: boolean): CodeOption[] {
    const items = cache.value[queryId] || []
    if (addAll) {
      return [{ label: '전체', value: '' }, ...items]
    }
    return items
  }

  function isLoaded(queryId: string): boolean {
    return queryId in cache.value
  }

  return { cache, loading, loadMulti, options, isLoaded }
})
