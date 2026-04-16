export type Lang = 'en-US' | 'ko-KR' | 'pl-PL';

// 모든 언어별 JSON 파일 경로 매핑
export const localeFiles: Record<Lang, Record<string, any>> = {
  'en-US': import.meta.glob('@/locales/en-US/**/*.json', { eager: true }),
  'ko-KR': import.meta.glob('@/locales/ko-KR/**/*.json', { eager: true }),
  'pl-PL': import.meta.glob('@/locales/pl-PL/**/*.json', { eager: true }),
};

export async function loadLocaleMessages(lang: Lang) {
  const entries = Object.entries(localeFiles[lang]); // [경로, 모듈] 배열

  return entries.reduce(
    (acc, [path, mod]) => {
      // 파일명만 추출: 경로에서 마지막 / 이후, 확장자 제거
      const fileName = path.split('/').pop()?.replace('.json', '') ?? 'unknown';

      acc[fileName] = mod.default || mod; // 네임스페이스로 할당

      return acc;
    },
    {} as Record<string, any>
  );
}
