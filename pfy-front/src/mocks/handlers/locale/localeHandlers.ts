import { http, HttpResponse } from 'msw';

/** axios 인터셉터가 POST 본문을 { header, payload: { ... } } 로 감쌈 */
function readWindowIdFromBody(body: unknown): string | undefined {
  if (!body || typeof body !== 'object') return undefined;
  const o = body as Record<string, unknown>;
  if (typeof o.windowId === 'string' && o.windowId.trim()) {
    return o.windowId.trim();
  }
  const payload = o.payload;
  if (payload && typeof payload === 'object') {
    const p = payload as Record<string, unknown>;
    if (typeof p.windowId === 'string' && p.windowId.trim()) {
      return p.windowId.trim();
    }
  }
  return undefined;
}

function okWithPayload(payload: Record<string, string>) {
  return HttpResponse.json({
    header: { responseCode: 'S0000', responseMessage: 'OK' },
    payload,
  });
}

export const localeHandlers = [
  http.post(
    /\/online\/mvcJson\/SYCC060-i18nWindowObjectList$/i,
    async ({ request }) => {
      let body: unknown;
      try {
        body = await request.json();
      } catch {
        return HttpResponse.json(
          { message: 'Invalid JSON body' },
          { status: 400 }
        );
      }

      const windowId = readWindowIdFromBody(body);
      if (!windowId) {
        return HttpResponse.json(
          { message: '동적 다국어 로딩 실패 (windowId 없음)' },
          { status: 400 }
        );
      }

      const messageData: Record<string, Record<string, string>> = {
        MTOV010: {
          'staText.mtov020':
            'Dynamically loaded i18n (English) MTOV020 mtov020',
        },
        DSOV010: {
          'staText.dsov010':
            'Dynamically loaded i18n (English) DSOV010 dsov010',
          'staText.dsov020':
            'Dynamically loaded i18n (English) DSOV020 dsov020',
        },
        MTCT010: {
          staNatnCd: '동적으로가져온단어에요',
          staSaveDraft: '동적으로 가져온 SaveDraft',
        },
        /** template-a~d · SCREEN_ID 미리보기 (main.ts changeLocale(..., 'TEMPLATE')) */
        TEMPLATE: {},
        PMDP040: {},
      };

      const windowData = messageData[windowId.toUpperCase()];
      if (!windowData) {
        return okWithPayload({});
      }

      return okWithPayload(windowData);
    }
  ),
];
