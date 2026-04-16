import type { ToastServiceMethods } from 'primevue/toastservice';
import type { Router } from 'vue-router';

import { clearClientSession } from '@/utils/clearSession';

type ConfirmFn = (opts: any) => void;
let confirmService: ConfirmFn | null = null;
let globalRouter: Router | null = null;
let toastService: ToastServiceMethods | null = null;

interface ErrorInfo {
  errorCode?: string;
  errorMessage?: string;
  errorType?: string;
}

export const initErrorUI = (deps: {
  toast: ToastServiceMethods;
  confirm: ConfirmFn;
  router: Router;
}) => {
  toastService = deps.toast;
  confirmService = deps.confirm;
  globalRouter = deps.router;
};

type Severity = 'success' | 'info' | 'warn' | 'error';

let lastErrorToastAt = 0;
const ERR_DEBOUNCE_MS = 1000;

const emitToast = (opts: {
  severity?: Severity;
  summary?: string;
  detail?: string;
  life?: number;
}) => {
  const severity = (opts?.severity ?? 'info') as Severity;

  if (severity === 'success' || severity === 'info') {
    toastService?.add(opts);
    return;
  }
  const now = Date.now();
  if (now - lastErrorToastAt < ERR_DEBOUNCE_MS) return;

  lastErrorToastAt = now;
  toastService?.add(opts);
};

export const handleAxiosError = (
  status?: number,
  message?: string,
  ei?: ErrorInfo
) => {
  const msg = message || 'Request failed';

  switch (status) {
    case 400:
      emitToast({
        severity: 'error',
        summary: 'Bad Request',
        detail: msg,
        life: 5000,
      });
      break;

    case 401:
    case 403: {
      if (ei?.errorCode === 'INVALID_TOKEN') {
        confirmService?.({
          header: 'Session Expired',
          message: 'Your session has expired.',
          acceptLabel: 'Go to Login Page',
          rejectLabel: 'Close',
          accept: () => {
            clearClientSession();
            if (globalRouter)
              setTimeout(() => globalRouter!.replace('/auth/login'), 0);
          },
        });
        return;
      }

      if (
        ei?.errorType === 'AUTH' &&
        (ei?.errorMessage ?? '').includes('BadCredentialsException')
      ) {
        emitToast({
          severity: 'error',
          summary: 'Login Failed',
          detail: 'Incorrect user ID or password.',
          life: 4000,
        });
        return;
      }

      emitToast({
        severity: 'warn',
        summary: 'Access Denied',
        detail: ei?.errorMessage || 'You do not have permission.',
        life: 4000,
      });
      break;
    }

    case 404:
      emitToast({
        severity: 'warn',
        summary: 'Not Found',
        detail: msg,
        life: 4000,
      });
      break;

    case 500:
      emitToast({
        severity: 'error',
        summary: 'Server Error',
        detail: 'An unexpected server error occurred.',
        life: 6000,
      });
      break;

    default:
      emitToast({
        severity: 'error',
        summary: 'Error',
        detail: msg,
        life: 5000,
      });
      break;
  }
};

export const showNoAuthToast = () => {
  emitToast({
    severity: 'error',
    summary: 'Access Denied',
    detail: 'You do not have permission to access this page.',
    life: 3000,
  });
};
