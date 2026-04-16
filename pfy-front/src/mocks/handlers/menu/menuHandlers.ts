import { http, HttpResponse } from 'msw';

export const menuHandlers = [
  http.post('/online/mvcJson/SYAR050-selectUserRoleMenuList', () => {
    const menuItems = [
      {
        menuNm: 'Dashboard',
        menuId: 'DSOV020',
      },
      {
        menuNm: 'Master Data Management',
        menuId: 'MD',
        children: [
          {
            menuNm: 'Master',
            menuId: 'MDPJ010',
          },
          {
            menuNm: 'Material Master',
            menuId: 'MNOD060',
          },
          {
            menuNm: 'BOM',
            menuId: 'MNOD050',
          },
          {
            menuNm: 'Work Process',
            menuId: 'WP',
            children: [
              {
                menuNm: '체계관리',
                menuId: 'MNOD090',
              },
              {
                menuNm: '업무별진행상태관리',
                menuId: 'MNPS010',
              },
            ],
          },
          {
            menuNm: 'Work Master Data',
            menuId: 'WM',
          },
        ],
      },
      {
        menuNm: 'Spare Parts',
        menuId: 'SP',
        children: [
          { menuNm: 'Overview', menuId: 'SPOV010' },
          {
            menuNm: 'Statistics',
            menuId: 'SPST010',
          },
          {
            menuNm: 'Order_MRO',
            menuId: 'SPOD010',
          },
          {
            menuNm: 'Order_Warehouse',
            menuId: 'SPOD020',
          },
          {
            menuNm: 'Confirmation',
            menuId: 'SPCF010',
          },
          {
            menuNm: 'Quotation Request',
            menuId: 'SPQR010',
          },
          { menuNm: 'Invoice', menuId: 'SPIV010' },
        ],
      },
      {
        menuNm: 'Maintenance',
        menuId: 'MT',
        children: [
          { menuNm: 'Overview', menuId: 'MTOV010' },
          {
            menuNm: 'Statistics',
            menuId: 'MTST010',
          },
          {
            menuNm: 'Contract Information',
            menuId: 'MTCT010',
          },
          {
            menuNm: 'Maintenance Quotation',
            menuId: 'MTQT010',
          },
          {
            menuNm: 'Maintenance Inquiry',
            menuId: 'MTIQ010',
          },
        ],
      },
      {
        menuNm: 'Help Center',
        menuId: 'HC',
        children: [
          { menuNm: 'Notice', menuId: 'HCNT010' },
          {
            menuNm: 'Technical Support',
            menuId: 'HCTI010',
          },
        ],
      },
      {
        menuNm: 'Inventory Management',
        menuId: 'IM',
        children: [{ menuNm: 'Inventory', menuId: 'IMIR010' }],
      },
      {
        menuNm: 'System Management',
        menuId: 'SY',
        children: [
          {
            menuNm: 'Common',
            menuId: 'SYCC',
            children: [
              {
                menuNm: 'Common Code',
                menuId: 'SYCC010',
              },
              {
                menuNm: 'Messages',
                menuId: 'SYCC020',
              },
              {
                menuNm: 'Form',
                menuId: 'SYCC030',
              },
              {
                menuNm: 'Organization',
                menuId: 'SYCC040',
              },
              {
                menuNm: 'Template',
                menuId: 'SYCC050',
              },
              {
                menuNm: 'Multilingual',
                menuId: 'SYCC060',
              },
              {
                menuNm: 'Multilingual Term',
                menuId: 'SYCC070',
              },
            ],
          },
          {
            menuNm: 'Access Rights',
            menuId: 'SYAR',
            children: [
              {
                menuNm: 'Access IP',
                menuId: 'SYAR010',
              },
              {
                menuNm: 'Menu',
                menuId: 'SYAR020',
              },
              {
                menuNm: 'Screen',
                menuId: 'SYAR030',
              },
              {
                menuNm: 'Role',
                menuId: 'SYAR040',
              },
              {
                menuNm: 'Menu by Role',
                menuId: 'SYAR050',
              },
              {
                menuNm: 'Screen by Role',
                menuId: 'SYAR060',
              },
              {
                menuNm: 'Roles by User',
                menuId: 'SYAR070',
              },
            ],
          },
          {
            menuNm: 'Log',
            menuId: 'SYLG',
            children: [
              {
                menuNm: 'System Access',
                menuId: 'SYLG010',
              },
              {
                menuNm: 'Screen Access',
                menuId: 'SYLG020',
              },
              {
                menuNm: 'File download',
                menuId: 'SYLG030',
              },
              {
                menuNm: 'Mail',
                menuId: 'SYLG040',
              },
              {
                menuNm: 'Error',
                menuId: 'SYLG050',
              },
            ],
          },
          {
            menuNm: 'Batch Job',
            menuId: 'SYBJ',
            children: [
              {
                menuNm: 'Schedule',
                menuId: 'SYBJ010',
              },
              {
                menuNm: 'Execution',
                menuId: 'SYBJ020',
              },
              { menuNm: 'Log', menuId: 'SYBJ030' },
            ],
          },
        ],
      },
    ];

    return HttpResponse.json({
      header: {
        responseCode: 'S0000',
        responseMessage: '성공',
      },
      payload: menuItems,
    });
  }),
];
