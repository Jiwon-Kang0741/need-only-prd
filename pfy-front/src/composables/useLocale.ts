import { computed } from 'vue';

import i18n from '@/plugins/i18n';
import { useUserStore } from '@/stores/userStore';
import { loadWindowLocale } from '@/utils/loadWindowLocale';

export function useLocale() {
  const userStore = useUserStore();

  // 사용자 언어 (없으면 'en-US' 기본)
  const locale = computed(() => userStore.user?.langCd ?? 'en-US');

  async function changeLocale(
    newLocale: 'en-US' | 'ko-KR' | 'pl-PL',
    windowId?: string
  ) {
    // if (locale.value === newLocale && !windowId) return; // 중복 방지

    if (windowId) {
      await loadWindowLocale(windowId);
    }

    // 언어 상태 변경
    i18n.global.locale.value = newLocale;

    // userStore에 반영
    if (userStore.user) {
      userStore.user.langCd = newLocale;
    }
  }

  return {
    locale,
    changeLocale,
  };
}
