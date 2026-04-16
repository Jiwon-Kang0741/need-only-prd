import { http, HttpResponse } from 'msw';

export const commonCodeHandlers = [
  http.post('/online/mvcJson/SYCC010-selectCodeComboMulti', async () => {
    return HttpResponse.json({ payload: {} });
  }),

  http.post('/online/mvcJson/SYCC010-selectCommCodeList', async () => {
    return HttpResponse.json({ payload: {} });
  }),
];
