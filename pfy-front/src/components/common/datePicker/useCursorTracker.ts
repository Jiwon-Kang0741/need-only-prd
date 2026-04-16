import { useActiveElement } from '@vueuse/core';
import { ref, watch } from 'vue';

export function useCursorTracker() {
  const cursorPos = ref(0);
  const activeElement = useActiveElement();

  watch(activeElement, (el) => {
    if (el instanceof HTMLInputElement) {
      setTimeout(() => {
        cursorPos.value = el.selectionStart ?? 0;
      }, 0);
    }
  });

  return { cursorPos };
}

export function useRangeCursorTracker() {
  const cursorPos = ref(0);
  const focused = ref<'start' | 'end'>('start');
  const activeElement = useActiveElement();

  watch(activeElement, (el) => {
    if (!(el instanceof HTMLInputElement)) return;
    setTimeout(() => {
      if (el && el.classList.contains('start-input')) {
        focused.value = 'start';
        cursorPos.value = (el as HTMLInputElement).selectionStart ?? 0;
      } else if (el && el.classList.contains('end-input')) {
        focused.value = 'end';
        cursorPos.value = (el as HTMLInputElement).selectionStart ?? 0;
      }
    });
  });

  return { cursorPos, focused };
}
