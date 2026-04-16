import { onBeforeMount, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { useLocale } from '@/composables/useLocale';

export function useWindowLocale(windowId: string) {
  const { t: rawT } = useI18n();
  const { locale, changeLocale } = useLocale();

  const loadLocale = async () => {
    await changeLocale(locale.value, windowId);
  };

  onBeforeMount(loadLocale);
  watch(locale, loadLocale);

  const tWithWindowId = (key: string, values?: any) =>
    rawT(`${windowId}.${key}`, values);

  return {
    t: tWithWindowId,
    locale,
  };
}
