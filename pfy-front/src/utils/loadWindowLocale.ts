import { merge } from 'lodash';

import { type Lang, loadLocaleMessages, localeFiles } from '@/locales';
import i18n from '@/plugins/i18n';

const commonLoaded: Record<Lang, boolean> = {
  'en-US': false,
  'ko-KR': false,
  'pl-PL': false,
};

export async function loadWindowLocale(windowId: string) {
  const lang = i18n.global.locale.value as Lang;

  if (!commonLoaded[lang]) {
    const messages = await loadLocaleMessages(lang);
    i18n.global.setLocaleMessage(lang, messages);
    commonLoaded[lang] = true;
  }

  let dynamicMessages: Record<string, any> = {};

  try {
    const langFiles = localeFiles[lang];
    const targetFileName = windowId.toUpperCase();
    const entry = Object.entries(langFiles).find(([path]) =>
      path.endsWith(`/${targetFileName}.json`)
    );

    if (entry) {
      const [, module] = entry;
      const localMessages = module.default || module;
      dynamicMessages = merge({}, dynamicMessages, localMessages);
    }
  } catch (e) {
    console.warn(`Failed to load local messages for ${windowId} (${lang})`, e);
  }

  i18n.global.mergeLocaleMessage(lang, {
    [windowId]: dynamicMessages,
  });
}
