import 'primeicons/primeicons.css';
import './styles/main.scss';

import Aura from '@primeuix/themes/aura';
import { createVCodeBlock } from '@wdns/vue-code-block';
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';
import { ProgressSpinner } from 'primevue';
import PrimeVue from 'primevue/config';
import ConfirmationService from 'primevue/confirmationservice';
import ConfirmDialog from 'primevue/confirmdialog';
import ToastService from 'primevue/toastservice';
import Tooltip from 'primevue/tooltip';
import { createApp } from 'vue';
import App from '@/App.vue';
import { useLocale } from '@/composables/useLocale';
import safeHtml from '@/directives/safeHtml';
import i18n from '@/plugins/i18n';
import { router } from '@/router';
import { useUserStore } from '@/stores/userStore';

if (import.meta.env.VITE_MOCK === 'true') {
  const { worker } = await import('./mocks/browser');
  await worker.start({ onUnhandledRequest: 'bypass' });
}


async function initializeUserSettings() {
  const userStore = useUserStore();
  const { changeLocale } = useLocale();

  const currentPath = window.location.pathname;

  const { user } = userStore;
  if (!user) {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      /** 개발용 템플릿 미리보기 — 토큰 없이 단독 접근 허용 */
      const templatePaths = ['/template-a', '/template-b', '/template-c', '/template-d'];
      if (templatePaths.includes(currentPath)) {
        await changeLocale('ko-KR', 'TEMPLATE');
        return;
      }
      /** Mockup 미리보기 — 로그인 없이 고객 시연용 접근 허용 */
      if (currentPath.startsWith('/mockup/')) {
        await changeLocale('ko-KR', 'MOCKUP');
        return;
      }
      /** 자동 생성 목업 페이지 — 로그인 없이 접근 허용 */
      if (currentPath.startsWith('/generated/') || currentPath === '/mockup/builder') {
        await changeLocale('ko-KR', 'MOCKUP');
        return;
      }
      await router.push('/auth/login');
      return;
    }

    console.warn('사용자 정보 API(@/api/auth) 없음 — MockUp 전용 모드');
    await changeLocale('ko-KR', 'MOCKUP');
    return;
  } else {
    await changeLocale(user.langCd);
  }
}

async function bootstrap() {
  const app = createApp(App);
  const pinia = createPinia();
  const VCodeBlock = createVCodeBlock({ persistentCopyButton: true });

  app.use(router);
  pinia.use(piniaPluginPersistedstate);
  app.use(pinia);
  app.use(PrimeVue, {
    theme: {
      preset: Aura,
      cssLayer: false,
      unstyled: false,
      options: { darkModeSelector: '.dark' },
    },
  });
  app.use(i18n);
  app.use(VCodeBlock);
  app.use(ConfirmationService);
  app.use(ToastService);
  app.directive('safe-html', safeHtml);
  app.directive('tooltip', Tooltip);
  app.component('ConfirmDialog', ConfirmDialog);
  app.component('ProgressSpinner', ProgressSpinner);

  await initializeUserSettings();
  await router.isReady();
  app.mount('#app');
}

bootstrap().catch((err) => {
  console.error('Failed to initialize app:', err);
});
