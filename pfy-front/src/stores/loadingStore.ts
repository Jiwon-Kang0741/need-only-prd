import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

export const useLoadingStore = defineStore('loading', () => {
  const loadingCount = ref(0);
  const isShowing = ref(false);
  let timer: ReturnType<typeof setTimeout> | null = null;

  function start() {
    loadingCount.value += 1;
    if (!isShowing.value) {
      isShowing.value = true;
    }
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function end() {
    if (loadingCount.value > 0) loadingCount.value -= 1;
    if (loadingCount.value === 0) {
      timer = setTimeout(() => {
        isShowing.value = false;
        timer = null;
      }, 200); // 최소 200ms 유지
    }
  }

  const isLoading = computed(() => isShowing.value);

  return { start, end, isLoading };
});
