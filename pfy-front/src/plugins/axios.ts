import axios from 'axios';

import { useLoadingStore } from '@/stores/loadingStore';
import { clearClientSession } from '@/utils/clearSession';
import { handleAxiosError } from '@/utils/errorHandler';
import { formatErrorMessage } from '@/utils/formatErrorMessage';

const isMock = import.meta.env.VITE_MOCK === 'true';

/**
 * Mock 모드: MSW 서비스워커는 '같은 오리진' 요청만 가로챔.
 * 절대 URL(http://localhost:8085)을 쓰면 Vite 포트가 달라질 때 CORS 에러.
 * → Mock 시에는 반드시 빈 문자열(상대 URL) 사용.
 */
const baseURL = isMock ? '' : (import.meta.env.VITE_API_BASE_URL || '');

const api = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

let loadingStore: ReturnType<typeof useLoadingStore> | null = null;

api.interceptors.request.use((originalConfig) => {
  if (!loadingStore) {
    loadingStore = useLoadingStore();
  }
  loadingStore.start();

  const url = originalConfig.url || '';
  const isLoginRequest = url.startsWith('/online/api/');
  const isFileRequest = url.startsWith('/online/files/');
  const token = localStorage.getItem('accessToken');

  const config = { ...originalConfig };

  if (
    config.method?.toLowerCase() === 'post' &&
    config.data &&
    typeof config.data === 'object' &&
    !isLoginRequest &&
    !isFileRequest &&
    !('header' in config.data && 'payload' in config.data)
  ) {
    if (token && config.headers?.set) {
      config.headers.set('Authorization', `Bearer ${token}`);
    }

    config.data = {
      header: {},
      payload: config.data,
    };
  }

  return config;
});

api.interceptors.response.use(
  (response) => {
    if (!loadingStore) {
      loadingStore = useLoadingStore();
    }
    loadingStore.end();

    const url = response.config.url || '';
    const isLoginResponse = url.startsWith('/online/api/');
    const isFileResponse = url.startsWith('/online/files/');

    if ((isLoginResponse || isFileResponse) && response.data?.errorInfo) {
      const { errorInfo } = response.data;
      const msg = errorInfo.errorMessage || 'Login failed';

      return Promise.reject(
        Object.assign(new Error(msg), {
          response: {
            status: errorInfo.status,
            data: { errorInfo },
            config: response.config,
          },
          normalizedMessage: msg,
        })
      );
    }

    const header = response.data?.header;
    if (
      !isLoginResponse &&
      !isFileResponse &&
      header?.responseCode &&
      header.responseCode !== 'S0000'
    ) {
      const msg = formatErrorMessage(
        { response: { data: response.data } },
        'Server Error'
      );

      // 비즈니스 오류 전역 토스트
      handleAxiosError(200, msg);

      return Promise.reject(
        Object.assign(new Error(msg), {
          response: {
            status: 200,
            data: response.data,
            config: response.config,
          },
          normalizedMessage: msg,
        })
      );
    }

    return response;
  },

  async (error) => {
    if (!loadingStore) loadingStore = useLoadingStore();
    loadingStore.end();

    const ei = error?.response?.data?.errorInfo;
    const header = error?.response?.data?.header;
    const status = error?.response?.status;

    const msg =
      ei?.errorMessage ||
      header?.responseMessage ||
      error?.response?.statusText ||
      error?.message ||
      'Request failed';

    if (ei?.errorCode === 'INVALID_TOKEN') {
      try {
        clearClientSession?.();
      } catch (logoutErr) {
        console.warn('Server logout failed:', logoutErr);
      } finally {
        if (window.location.pathname !== '/auth/login') {
          window.location.replace('/auth/login');
        }
      }
      return Promise.reject(error);
    }

    handleAxiosError(status, msg, ei);

    return Promise.reject(
      Object.assign(new Error(msg), {
        response: error?.response,
        config: error?.config,
        normalizedMessage: msg,
      })
    );
  }
);

export default api;
