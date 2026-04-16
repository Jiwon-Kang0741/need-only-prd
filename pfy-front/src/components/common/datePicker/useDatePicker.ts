import dayjs from 'dayjs';
import { ComputedRef, type Ref, ref, watch } from 'vue';

import { useCursorTracker } from './useCursorTracker';

type ViewType = 'date' | 'month';

export function useDatePicker(
  params: {
    modelValue: Date | null;
    view: Ref<ViewType> | ComputedRef<ViewType>;
  },
  popover: Ref<any>,
  emit: (e: 'update:modelValue', value: Date | null) => void
) {
  const inputRef = ref<HTMLInputElement | null>(null);
  const displayValue = ref('');
  const localValue = ref<Date | null>(params.modelValue ?? null);
  const { view } = params;
  const { cursorPos } = useCursorTracker();

  // 날짜 포맷
  const formatDate = (date: Date, viewMode: 'date' | 'month'): string => {
    return viewMode === 'month'
      ? dayjs(date).format('YYYY-MM')
      : dayjs(date).format('YYYY-MM-DD');
  };

  // Date 변환
  const parseDate = (val: string): Date | null => {
    const cleaned = val.trim();

    if (view.value === 'month') {
      const match = cleaned.match(/^(\d{4})-(\d{2})$/);
      if (!match) return null;
      const [, y, m] = match;
      const date = new Date(+y, +m - 1);
      return Number.isNaN(date.getTime()) ? null : date;
    }

    const match = cleaned.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return null;
    const [, y, m, d] = match;
    const date = new Date(+y, +m - 1, +d);

    if (
      date.getFullYear() !== +y ||
      date.getMonth() + 1 !== +m ||
      date.getDate() !== +d
    ) {
      return null;
    }

    return date;
  };

  // 커서 위치로 단위 판별
  const getUnit = () => {
    const pos = cursorPos.value;

    // month view
    if (view.value === 'month') {
      return pos <= 4 ? 'year' : 'month'; // '2025-08'
    }

    // default: date view
    if (pos <= 4) return 'year';
    if (pos <= 7) return 'month';

    return 'day';
  };

  // 날짜 증감 로직
  const step = (delta: number) => {
    const date = parseDate(displayValue.value);
    if (!date) return;

    const unit = getUnit();
    const newDate = new Date(date);

    if (unit === 'year') newDate.setFullYear(date.getFullYear() + delta);
    else if (unit === 'month') newDate.setMonth(date.getMonth() + delta);
    else if (unit === 'day' && view.value === 'date') {
      newDate.setDate(date.getDate() + delta);
    } else {
      // month 뷰에서 day 단위 요청 시 무시
      return;
    }
    displayValue.value = formatDate(newDate, view.value as 'month' | 'date');
    localValue.value = newDate;
    emit('update:modelValue', localValue.value);
  };

  // 날짜 선택
  const onDateSelect = (value: Date) => {
    // InputText에 포맷 표시
    displayValue.value = formatDate(value, view.value as 'month' | 'date');

    // 부모에 Date emit
    emit('update:modelValue', value);
    popover.value?.hide();
  };

  // modelValue → 내부 상태 반영
  watch(
    () => params.modelValue,
    (val) => {
      const parsed = typeof val === 'string' ? parseDate(val) : val;
      if (parsed instanceof Date && !Number.isNaN(parsed.getTime())) {
        displayValue.value = formatDate(parsed, view.value as 'month' | 'date');
        localValue.value = parsed;
      } else {
        displayValue.value = '';
        localValue.value = null;
      }
    },
    { immediate: true }
  );

  // localValue → emit + displayValue 갱신
  watch(localValue, (val) => {
    if (val instanceof Date) {
      displayValue.value = formatDate(val, view.value as 'month' | 'date');
      emit('update:modelValue', val);
    }
  });

  // displayValue 입력 → localValue + emit
  watch(displayValue, (val) => {
    const parsed = parseDate(val);
    if (parsed) {
      localValue.value = parsed;
      emit('update:modelValue', parsed);
    }
  });

  return {
    inputRef,
    displayValue,
    localValue,
    step,
    cursorPos,
    onDateSelect,
  };
}
