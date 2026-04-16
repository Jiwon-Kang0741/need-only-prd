import { createI18n } from 'vue-i18n';

import { type Lang, loadLocaleMessages } from '@/locales';

// fallback 포함 초기 언어 설정
const defaultLocale: Lang = 'en-US';

const i18n = createI18n({
  legacy: false,
  locale: defaultLocale,
  fallbackLocale: 'en-US',
  messages: {},
  flatJson: true,
});

loadLocaleMessages(defaultLocale).then((msgs) => {
  i18n.global.setLocaleMessage(defaultLocale, msgs);
});

export default i18n;
