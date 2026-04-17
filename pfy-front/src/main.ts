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

if (import.meta.env.VITE_MOCK === 'true') {
  const { worker } = await import('./mocks/browser');
  await worker.start({ onUnhandledRequest: 'bypass' });
}


async function initializeUserSettings() {
  // need-only-prd에서는 pfy-front를 Mockup 렌더링 런타임으로만 사용한다.
  // 따라서 인증/로그인은 불필요 — 항상 MOCKUP 로케일로 초기화한다.
  const { changeLocale } = useLocale();
  await changeLocale('ko-KR', 'MOCKUP');
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
