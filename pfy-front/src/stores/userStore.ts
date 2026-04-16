import { debounce } from 'lodash';
import { defineStore } from 'pinia';
import { useToast } from 'primevue/usetoast';
import { ref, watch } from 'vue';

import i18n from '@/plugins/i18n';
import type { UserInfo } from '@/types/user';

const AVAILABLE_LANGUAGES = ['en-US', 'ko-KR', 'pl-PL'] as const;
type LangCd = (typeof AVAILABLE_LANGUAGES)[number];

const AVAILABLE_THEMES = ['light', 'dark'] as const;
type SknCd = (typeof AVAILABLE_THEMES)[number];

// 유효성 체크 함수
const isValidLang = (lang: string): lang is LangCd =>
  AVAILABLE_LANGUAGES.includes(lang as LangCd);

const isValidTheme = (theme: string): theme is SknCd =>
  AVAILABLE_THEMES.includes(theme as SknCd);

export const useUserStore = defineStore(
  'userStore',
  () => {
    const toast = useToast();
    const user = ref<UserInfo | null>(null);
    const sknCd = ref<SknCd>('light');
    const langCd = ref<LangCd>('en-US');
    const menuUpdated = ref(false);

    const $reset = () => {
      user.value = null;
      sknCd.value = 'light';
      langCd.value = 'en-US';
    };

    const updateHtmlClass = (theme: SknCd) => {
      document.documentElement.classList.toggle('dark', theme === 'dark');
    };

    const setUser = (userInfo: UserInfo) => {
      user.value = userInfo;
      if (isValidTheme(userInfo.sknCd)) {
        sknCd.value = userInfo.sknCd;
        updateHtmlClass(sknCd.value);
      }
      if (isValidLang(userInfo.langCd)) {
        langCd.value = userInfo.langCd;
        i18n.global.locale.value = langCd.value;
      }
    };

    const updateUser = (partial: Partial<UserInfo>) => {
      if (!user.value) return;
      user.value = { ...user.value, ...partial };
    };

    const saveUserSettings = debounce(() => {
      if (!user.value) return;
      updateUser({
        langCd: langCd.value,
        sknCd: sknCd.value,
      });
      menuUpdated.value = !menuUpdated.value;
      i18n.global.locale.value = langCd.value;
    }, 500);

    watch(
      [sknCd, langCd],
      () => {
        updateHtmlClass(sknCd.value);
        saveUserSettings();
      },
      { immediate: true }
    );

    const loadUserSettings = () => {
      if (!user.value) return;

      const theme = user.value.sknCd?.toLowerCase();
      const lang = user.value.langCd;

      sknCd.value = isValidTheme(theme) ? theme : 'light';
      langCd.value = isValidLang(lang) ? lang : 'en-US';

      updateHtmlClass(sknCd.value);
    };

    const toggleTheme = () => {
      sknCd.value = sknCd.value === 'dark' ? 'light' : 'dark';
    };

    const setSknCd = (value: string) => {
      if (isValidTheme(value)) sknCd.value = value;
    };

    const setLangCd = (value: string) => {
      if (isValidLang(value)) langCd.value = value;
    };

    return {
      user,
      sknCd,
      langCd,
      menuUpdated,
      setUser,
      loadUserSettings,
      toggleTheme,
      setSknCd,
      setLangCd,
      $reset,
    };
  },
  {
    persist: true,
  }
);
