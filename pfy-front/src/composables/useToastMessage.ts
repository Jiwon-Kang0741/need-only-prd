import { useToast } from 'primevue/usetoast';
import { useI18n } from 'vue-i18n';

interface ToastOptions {
  severity?: string;
  summary?: string;
  detail?: string;
  life?: number;
  group?: string;
  closable?: boolean;
  styleClass?: string;
  contentStyleClass?: string;
  i18n?: boolean;
  closeIcon?: string;
  infoIcon?: string;
  warnIcon?: string;
  errorIcon?: string;
  successIcon?: string;
  messageIcon?: string;

  // 커스텀 확장 속성 (PrimeVue에는 없음)
  sticky?: boolean;
  icon?: string;
  toastId?: string;
}

export const useToastMessage = () => {
  const toast = useToast();
  const { t } = useI18n();
  const activeToasts = new Set<string>();
  const showToast = (options: ToastOptions) => {
    const {
      severity = 'info',
      summary,
      detail,
      life = 3000,
      group,
      closable,
      styleClass,
      contentStyleClass,
      i18n = true,
      sticky = false,
      toastId,
      closeIcon,
      infoIcon,
      warnIcon,
      errorIcon,
      successIcon,
      messageIcon,
    } = options;

    const translateIfNeeded = (text?: string): string | undefined => {
      // if (!text) return undefined;
      // return i18n ? t(text) : text;
      return text;
    };

    // PrimeVue 타입에 맞는 옵션만 추려서 넘김
    const toastOptions = {
      severity,
      summary: translateIfNeeded(summary),
      detail: translateIfNeeded(detail),
      life: sticky ? Infinity : life,
      group,
      closable,
      styleClass,
      contentStyleClass,
      toastId,
      closeIcon,
      infoIcon,
      warnIcon,
      errorIcon,
      successIcon,
      messageIcon,
    };

    if (toastId && activeToasts.has(toastId)) return;

    if (toastId) activeToasts.add(toastId);

    toast.add(toastOptions);

    if (toastId) {
      setTimeout(() => activeToasts.delete(toastId), life);
    }
  };

  const clear = () => {
    toast.removeAllGroups();
  };

  return {
    toast: showToast,
    clear,
  };
};
