import { http, HttpResponse } from 'msw';

export const routerHandlers = [
  http.post('/online/mvcJson/SYAR050-selectUserRoleWindowList', async () => {
    const routes = [
      {
        menuId: 'DSOV010',
        windowId: 'DSOV010',
        windowUrl: 'pages/ds/ov/dsov010/index.vue',
      },
      {
        menuId: 'DSOV020',
        windowId: 'DSOV020',
        windowUrl: 'pages/ds/ov/dsov020/index.vue',
      },

      // Spare Parts
      {
        menuId: 'SPOV010',
        windowId: 'SPOV010',
        windowUrl: 'pages/sp/ov/spov010/index.vue',
      },
      {
        menuId: 'SPST010',
        windowId: 'SPST010',
        windowUrl: 'pages/sp/st/spst010/index.vue',
      },
      {
        menuId: 'SPOD010',
        windowId: 'SPOD010',
        windowUrl: 'pages/sp/od/spod010/index.vue',
      },
      {
        menuId: 'SPOD020',
        windowId: 'SPOD020',
        windowUrl: 'pages/sp/od/spod020/:id',
      },
      {
        menuId: 'SPCF010',
        windowId: 'SPCF010',
        windowUrl: 'pages/sp/cf/spcf010/index.vue',
      },
      {
        menuId: 'SPCF010P01',
        windowId: 'SPCF010P01',
        windowUrl: 'pages/sp/cf/spcf010p01/index.vue',
      },
      {
        menuId: 'SPIV010',
        windowId: 'SPIV010',
        windowUrl: 'pages/sp/iv/spiv010/index.vue',
      },
      {
        menuId: 'SPQR010',
        windowId: 'SPQR010',
        windowUrl: 'pages/sp/qr/spqr010/index.vue',
      },
      {
        menuId: 'SPQR020',
        windowId: 'SPQR020',
        windowUrl: 'pages/sp/qr/spqr020/index.vue',
      },
      {
        menuId: 'SPQR030',
        windowId: 'SPQR030',
        windowUrl: 'pages/sp/qr/spqr030/index.vue',
      },
      {
        menuId: 'SPQR040',
        windowId: 'SPQR040',
        windowUrl: 'pages/sp/qr/spqr040/index.vue',
      },

      // Maintenance
      {
        menuId: 'MTRQ010',
        windowId: 'MTRQ010',
        windowUrl: 'pages/mt/rq/mtrq010/index.vue',
      },
      {
        menuId: 'MTOV010',
        windowId: 'MTOV010',
        windowUrl: 'pages/mt/ov/mtov010/index.vue',
      },
      {
        menuId: 'MTOV010P01',
        windowId: 'MTOV010P01',
        windowUrl: 'pages/mt/ov/mtov010p01/index.vue',
      },
      {
        menuId: 'MTQT010',
        windowId: 'MTQT010',
        windowUrl: 'pages/mt/qt/mtqt010/index.vue',
      },
      {
        menuId: 'MTIQ010',
        windowId: 'MTIQ010',
        windowUrl: 'pages/mt/iq/mtiq010/index.vue',
      },
      {
        menuId: 'MTIQ010P01',
        windowId: 'MTIQ010P01',
        windowUrl: 'pages/mt/iq/mtiq010p01/index.vue',
      },
      {
        menuId: 'MTIQ010P02',
        windowId: 'MTIQ010P02',
        windowUrl: 'pages/mt/iq/mtiq010p02/index.vue',
      },
      {
        menuId: 'MTCT010',
        windowId: 'MTCT010',
        windowUrl: 'pages/mt/ct/mtct010/index.vue',
      },
      {
        menuId: 'MTCT010P01',
        windowId: 'MTCT010P01',
        windowUrl: 'pages/mt/ct/mtct010p01/index.vue',
      },
      {
        menuId: 'MTST010',
        windowId: 'MTST010',
        windowUrl: 'pages/mt/st/mtst010/index.vue',
      },

      // Inventory Management
      {
        menuId: 'IMIR010',
        windowId: 'IMIR010',
        windowUrl: 'pages/im/ir/imir010/index.vue',
      },

      // Help Center
      {
        menuId: 'HCNT010',
        windowId: 'HCNT010',
        windowUrl: 'pages/hc/nt/hcnt010/index.vue',
      },
      {
        menuId: 'HCNT010P01',
        windowId: 'HCNT010P01',
        windowUrl: 'pages/hc/nt/hcnt010p01/index.vue',
      },
      {
        menuId: 'HCNT010P02',
        windowId: 'HCNT010P02',
        windowUrl: 'pages/hc/nt/hcnt010p02/index.vue',
      },
      {
        menuId: 'HCTI010',
        windowId: 'HCTI010',
        windowUrl: 'pages/hc/ti/hcti010/index.vue',
      },
      {
        menuId: 'HCTI010P01',
        windowId: 'HCTI010P01',
        windowUrl: 'pages/hc/ti/hcti010p01/index.vue',
      },
      {
        menuId: 'HCTI010P02',
        windowId: 'HCTI010P02',
        windowUrl: 'pages/hc/ti/hcti010p02/index.vue',
      },

      // System Management - Common
      {
        menuId: 'SYCC010',
        windowId: 'SYCC010',
        windowUrl: 'pages/sy/cc/sycc010/index.vue',
      },
      {
        menuId: 'SYCC010P01',
        windowId: 'SYCC010P01',
        windowUrl: 'pages/sy/cc/sycc010p01/index.vue',
      },
      {
        menuId: 'SYCC010P02',
        windowId: 'SYCC010P02',
        windowUrl: 'pages/sy/cc/sycc010p02/index.vue',
      },
      {
        menuId: 'SYCC020',
        windowId: 'SYCC020',
        windowUrl: 'pages/sy/cc/sycc020/index.vue',
      },
      {
        menuId: 'SYCC030',
        windowId: 'SYCC030',
        windowUrl: 'pages/sy/cc/sycc030/index.vue',
      },
      {
        menuId: 'SYCC040',
        windowId: 'SYCC040',
        windowUrl: 'pages/sy/cc/sycc040/index.vue',
      },
      {
        menuId: 'SYCC040P01',
        windowId: 'SYCC040P01',
        windowUrl: 'pages/sy/cc/sycc040p01/index.vue',
      },
      {
        menuId: 'SYCC050',
        windowId: 'SYCC050',
        windowUrl: 'pages/sy/cc/sycc050/index.vue',
      },
      {
        menuId: 'SYCC050P01',
        windowId: 'SYCC050P01',
        windowUrl: 'pages/sy/cc/SYCC050p01/index.vue',
      },
      {
        menuId: 'SYCC060',
        windowId: 'SYCC060',
        windowUrl: 'pages/sy/cc/sycc060/index.vue',
      },
      {
        menuId: 'SYCC060P01',
        windowId: 'SYCC060P01',
        windowUrl: 'pages/sy/cc/sycc060p01/index.vue',
      },
      {
        menuId: 'SYCC070',
        windowId: 'SYCC070',
        windowUrl: 'pages/sy/cc/sycc070/index.vue',
      },

      // System Management - Access Rights
      {
        menuId: 'SYAR010',
        windowId: 'SYAR010',
        windowUrl: 'pages/sy/ar/syar010/index.vue',
      },
      {
        menuId: 'SYAR020',
        windowId: 'SYAR020',
        windowUrl: 'pages/sy/ar/syar020/index.vue',
      },
      {
        menuId: 'SYAR030',
        windowId: 'SYAR030',
        windowUrl: 'pages/sy/ar/syar030/index.vue',
      },
      {
        menuId: 'SYAR030P01',
        windowId: 'SYAR030P01',
        windowUrl: 'pages/sy/ar/syar030p01/index.vue',
      },
      {
        menuId: 'SYAR040',
        windowId: 'SYAR040',
        windowUrl: 'pages/sy/ar/syar040/index.vue',
      },
      {
        menuId: 'SYAR040P01',
        windowId: 'SYAR040P01',
        windowUrl: 'pages/sy/ar/syar040p01/index.vue',
      },
      {
        menuId: 'SYAR050',
        windowId: 'SYAR050',
        windowUrl: 'pages/sy/ar/syar050/index.vue',
      },
      {
        menuId: 'SYAR060',
        windowId: 'SYAR060',
        windowUrl: 'pages/sy/ar/syar060/index.vue',
      },
      {
        menuId: 'SYAR070',
        windowId: 'SYAR070',
        windowUrl: 'pages/sy/ar/syar070/index.vue',
      },
      {
        menuId: 'SYAR090',
        windowId: 'SYAR090',
        windowUrl: 'pages/sy/ar/syar090/index.vue',
      },
      {
        menuId: 'SYAR090P01',
        windowId: 'SYAR090P01',
        windowUrl: 'pages/sy/ar/syar090p01/index.vue',
      },

      // System Management - Log
      {
        menuId: 'SYLG010',
        windowId: 'SYLG010',
        windowUrl: 'pages/sy/lg/sylg010/index.vue',
      },
      {
        menuId: 'SYLG020',
        windowId: 'SYLG020',
        windowUrl: 'pages/sy/lg/sylg020/index.vue',
      },
      {
        menuId: 'SYLG030',
        windowId: 'SYLG030',
        windowUrl: 'pages/sy/lg/sylg030/index.vue',
      },
      {
        menuId: 'SYLG040',
        windowId: 'SYLG040',
        windowUrl: 'pages/sy/lg/sylg040/index.vue',
      },
      {
        menuId: 'SYLG050',
        windowId: 'SYLG050',
        windowUrl: 'pages/sy/lg/sylg050/index.vue',
      },

      // System Management - Batch Job
      {
        menuId: 'SYBJ010',
        windowId: 'SYBJ010',
        windowUrl: 'pages/sy/bj/sybj010/index.vue',
      },
      {
        menuId: 'SYBJ010P01',
        windowId: 'SYBJ010P01',
        windowUrl: 'pages/sy/bj/sybj010p01/index.vue',
      },
      {
        menuId: 'SYBJ010P02',
        windowId: 'SYBJ010P02',
        windowUrl: 'pages/sy/bj/sybj010p02/index.vue',
      },
      {
        menuId: 'SYBJ010P03',
        windowId: 'SYBJ010P03',
        windowUrl: 'pages/sy/bj/sybj010p03/index.vue',
      },
      {
        menuId: 'SYBJ020',
        windowId: 'SYBJ020',
        windowUrl: 'pages/sy/bj/sybj020/index.vue',
      },
      {
        menuId: 'SYBJ020P01',
        windowId: 'SYBJ020P01',
        windowUrl: 'pages/sy/bj/sybj020p01/index.vue',
      },
      {
        menuId: 'SYBJ030',
        windowId: 'SYBJ030',
        windowUrl: 'pages/sy/bj/sybj030/index.vue',
      },

      // Master Data Management - Project
      {
        menuId: 'MDPJ010',
        windowId: 'MDPJ010',
        windowUrl: 'pages/md/pj/mdpj010/index.vue',
      },
      {
        menuId: 'MDPJ020',
        windowId: 'MDPJ020',
        windowUrl: 'pages/md/pj/mdpj020/index.vue',
      },
      {
        menuId: 'MDPJ030',
        windowId: 'MDPJ030',
        windowUrl: 'pages/md/pj/mdpj030/index.vue',
      },

      // Master Data Management - Others
      {
        menuId: 'MDCT010',
        windowId: 'MDCT010',
        windowUrl: 'pages/md/ct/mdct010/index.vue',
      },
      {
        menuId: 'MDCT010P01',
        windowId: 'MDCT010P01',
        windowUrl: 'pages/md/ct/mdct010p01/index.vue',
      },
      {
        menuId: 'MNOD090',
        windowId: 'MNOD090',
        windowUrl: 'pages/mn/od/mnod090/index.vue',
      },
      {
        menuId: 'MNPS010',
        windowId: 'MNPS010',
        windowUrl: 'pages/mn/ps/mnps010/index.vue',
      },
      {
        menuId: 'MDWH010',
        windowId: 'MDWH010',
        windowUrl: 'pages/md/wh/mdwh010/index.vue',
      },
      {
        menuId: 'MDCR010',
        windowId: 'MDCR010',
        windowUrl: 'pages/md/cr/mdcr010/index.vue',
      },
      {
        menuId: 'MDMG010',
        windowId: 'MDMG010',
        windowUrl: 'pages/md/mg/mdmg010/index.vue',
      },
      {
        menuId: 'MNOD060',
        windowId: 'MNOD060',
        windowUrl: 'pages/mn/od/mnod060/index.vue',
      },
      {
        menuId: 'MNOD050',
        windowId: 'MNOD050',
        windowUrl: 'pages/mn/od/mnod050/index.vue',
      },
    ];

    return HttpResponse.json({
      header: {
        responseCode: 'S0000',
        responseMessage: '성공',
      },
      payload: routes,
    });
  }),
];
