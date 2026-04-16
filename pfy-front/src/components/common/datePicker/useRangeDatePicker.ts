import dayjs from 'dayjs';
import { useToast } from 'primevue/usetoast';
import {
  type ComponentPublicInstance,
  computed,
  ComputedRef,
  type Ref,
  ref,
  watch,
} from 'vue';

import { useRangeCursorTracker } from './useCursorTracker';

type ViewType = 'date' | 'month';

export function useRangeDatePicker(
  params: {
    modelValue: [Date | null, Date | null];
    view: Ref<ViewType> | ComputedRef<ViewType>;
  },
  popover: Ref<any>,

  emit: (e: 'update:modelValue', value: [Date | null, Date | null]) => void
) {
  const startInputRef = ref<ComponentPublicInstance<any> | null>(null);
  const endInputRef = ref<ComponentPublicInstance<any> | null>(null);
  const { cursorPos, focused } = useRangeCursorTracker();
  const [initialStart, initialEnd] = params.modelValue;
  const startDate = ref<Date | null>(initialStart);
  const endDate = ref<Date | null>(initialEnd);
  const startDisplay = ref('');
  const endDisplay = ref('');

  const { view } = params;

  const toast = useToast();

  const showToast = (msg: string) => {
    toast.add({
      severity: 'warn',
      summary: '날짜 오류',
      detail: msg,
      life: 3000,
    });
  };

  // 날짜 포멧
  const formatDate = (date: Date, viewMode: 'date' | 'month') => {
    return viewMode === 'month'
      ? dayjs(date).format('YYYY-MM')
      : dayjs(date).format('YYYY-MM-DD');
  };

  // Date 변환
  const parseDate = (str: string): Date | null => {
    const match =
      view.value === 'month'
        ? str.match(/^(\d{4})-(\d{2})$/)
        : str.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return null;
    const [, y, m, d = '1'] = match;
    const date = new Date(+y, +m - 1, +d);
    return Number.isNaN(date.getTime()) ? null : date;
  };

  // 커서 위치로 단위 판별
  const getUnit = (): 'year' | 'month' | 'day' => {
    const pos = cursorPos.value;
    if (view.value === 'month') return pos <= 4 ? 'year' : 'month';
    if (pos <= 4) return 'year';
    if (pos <= 7) return 'month';
    return 'day';
  };

  // 날짜 증감 로직
  const step = (delta: number, target: 'start' | 'end') => {
    const targetDate = target === 'start' ? startDate.value : endDate.value;
    if (!targetDate) return;

    const unit = getUnit();
    const newDate = new Date(targetDate); // clone

    if (unit === 'year') newDate.setFullYear(newDate.getFullYear() + delta);
    else if (unit === 'month') newDate.setMonth(newDate.getMonth() + delta);
    else newDate.setDate(newDate.getDate() + delta);

    if (target === 'start') {
      startDate.value = newDate;
      startDisplay.value = formatDate(newDate, view.value);
    } else {
      endDate.value = newDate;
      endDisplay.value = formatDate(newDate, view.value);
    }

    emit('update:modelValue', [startDate.value, endDate.value]);
  };

  // 시작날짜 선택
  const onDateSelectStart = (val: Date) => {
    if (endDate.value && dayjs(val).isAfter(dayjs(endDate.value), 'day')) {
      showToast('시작일은 종료일보다 이후일 수 없습니다.');
      return;
    }
    if (endDate.value && dayjs(val).isSame(dayjs(endDate.value), 'day')) {
      showToast('시작일과 종료일이 같습니다.');
      return;
    }

    startDate.value = val;
    startDisplay.value = formatDate(val, view.value as 'month' | 'date');
  };

  // 종료날짜 선택
  const onDateSelectEnd = (val: Date) => {
    if (startDate.value && dayjs(val).isBefore(dayjs(startDate.value), 'day')) {
      showToast('종료일은 시작일보다 이전일 수 없습니다.');
      return;
    }
    if (startDate.value && dayjs(val).isSame(dayjs(startDate.value), 'day')) {
      showToast('시작일과 종료일이 같습니다.');
      return;
    }

    endDate.value = val;
    endDisplay.value = formatDate(val, view.value as 'month' | 'date');
  };

  // 시작일, 종료일 모두 선택 여부
  const rangeSelectCompleted = computed((): boolean => {
    return startDisplay.value !== '' && endDisplay.value !== '';
  });

  // 시작일 선택시 종료일에서 제외
  const disabledStartDates = computed(() => {
    if (!endDate.value || view.value !== 'date') return [];
    return [dayjs(endDate.value).startOf('day').toDate()];
  });

  // 종료일 선택시 시작일에서 제외
  const disabledEndDates = computed(() => {
    if (!startDate.value || view.value !== 'date') return [];
    return [dayjs(startDate.value).startOf('day').toDate()];
  });

  const onCancel = () => {
    popover.value?.hide();
    startDate.value = null;
    startDisplay.value = '';
    endDate.value = null;
    endDisplay.value = '';
  };

  const onConfirm = () => {
    emit('update:modelValue', [startDate.value, endDate.value]);
    popover.value?.hide();
  };

  // 입력 → 날짜 객체로 반영
  watch([startDisplay, endDisplay], ([s, e]) => {
    const sDate = parseDate(s);
    const eDate = parseDate(e);
    startDate.value = sDate;
    endDate.value = eDate;

    emit('update:modelValue', [startDate.value, endDate.value]);
  });

  // 외부 modelValue 변경 감지
  watch(
    () => params.modelValue,
    ([newStart, newEnd]) => {
      if (newStart) {
        startDate.value = newStart;
        startDisplay.value = formatDate(newStart, view.value);
      }
      if (newEnd) {
        endDate.value = newEnd;
        endDisplay.value = formatDate(newEnd, view.value);
      }
    },
    { immediate: true }
  );

  // 입력 → 날짜 객체로 반영
  watch([startDisplay, endDisplay], ([s, e]) => {
    const sDate = parseDate(s);
    const eDate = parseDate(e);
    startDate.value = sDate;
    endDate.value = eDate;

    emit('update:modelValue', [startDate.value, endDate.value]);
  });

  // 직접 입력 시 날짜 validation 체크
  watch([startDate, endDate], ([s, e]) => {
    if (!s || !e) return;

    if (dayjs(s).isAfter(dayjs(e), 'day')) {
      showToast('시작일은 종료일보다 이후일 수 없습니다.');
      startDate.value = null;
      startDisplay.value = '';
    } else if (dayjs(e).isBefore(dayjs(s), 'day')) {
      showToast('종료일은 시작일보다 이전일 수 없습니다.');
      endDate.value = null;
      endDisplay.value = '';
    }
  });

  return {
    startInputRef,
    endInputRef,
    startDate,
    endDate,
    startDisplay,
    endDisplay,
    cursorPos,
    focused,
    step,
    onDateSelectStart,
    onDateSelectEnd,
    onCancel,
    onConfirm,
    rangeSelectCompleted,
    disabledEndDates,
    disabledStartDates,
  };
}
