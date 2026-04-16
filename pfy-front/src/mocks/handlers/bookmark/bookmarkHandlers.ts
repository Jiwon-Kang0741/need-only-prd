import { http, HttpResponse } from 'msw';

export const bookmarkHandlers = [
  http.get('/api/bookmarks', () => {
    const bookmarks = [
      {
        menuNm: 'Dashboard',
        menuId: 'DSOV020',
      },
      {
        menuNm: 'Master',
        menuId: 'MDPJ010',
      },
      {
        menuNm: 'Overview',
        menuId: 'SPOV010',
      },
      {
        menuNm: 'Common Code',
        menuId: 'SYCC010',
      },
    ];

    return HttpResponse.json({
      success: true,
      data: bookmarks,
      message: 'Bookmarks retrieved successfully',
    });
  }),
];
