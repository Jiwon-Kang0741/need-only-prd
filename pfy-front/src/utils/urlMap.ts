export const urlMap: Record<string, () => Promise<any>> = {
  '/guide': () => import('@/pages/guide/features/DataTableGuide.vue'),
  '/popup/testLayer': () => import('@/pages/popup/TestLayer.vue'),

  // Dashboard
  '/ROOT01': () => import('@/pages/ds/ov/dsov010/index.vue'),
  '/DSOV020': () => import('@/pages/ds/ov/dsov020/index.vue'),

  // Spare Parts
  '/SPOV010': () => import('@/pages/sp/ov/spov010/index.vue'),
  '/SPST010': () => import('@/pages/sp/st/spst010/index.vue'),
  '/SPOD010': () => import('@/pages/sp/od/spod010/index.vue'),
  '/SPOD020': () => import('@/pages/sp/od/spod020/index.vue'),
  '/SPCF010': () => import('@/pages/sp/cf/spcf010/index.vue'),
  '/SPCF010P01': () => import('@/pages/sp/cf/spcf010p01/index.vue'),
  '/SPIV010': () => import('@/pages/sp/iv/spiv010/index.vue'),
  '/SPQR010': () => import('@/pages/sp/qr/spqr010/index.vue'),
  '/SPQR020': () => import('@/pages/sp/qr/spqr020/index.vue'),
  '/SPQR030': () => import('@/pages/sp/qr/spqr030/index.vue'),
  '/SPQR040': () => import('@/pages/sp/qr/spqr040/index.vue'),

  // Maintenance
  '/ROOT0401': () => import('@/pages/mt/ov/mtov010/index.vue'),
  '/MTOV010P01': () => import('@/pages/mt/ov/mtov010p01/index.vue'),
  '/MTQT010': () => import('@/pages/mt/qt/mtqt010/index.vue'),
  '/MTIQ010': () => import('@/pages/mt/iq/mtiq010/index.vue'),
  '/MTCT010': () => import('@/pages/mt/ct/mtct010/index.vue'),
  '/MTCT010P01': () => import('@/pages/mt/ct/mtct010p01/index.vue'),
  '/MTST010': () => import('@/pages/mt/st/mtst010/index.vue'),

  // Inventory Management
  '/IMIR010': () => import('@/pages/im/ir/imir010/index.vue'),

  // Help Center
  '/HCNT010': () => import('@/pages/hc/nt/hcnt010/index.vue'),
  '/HCNT010P01': () => import('@/pages/hc/nt/hcnt010p01/index.vue'),
  '/HCNT010P02': () => import('@/pages/hc/nt/hcnt010p02/index.vue'),
  '/HCTI010': () => import('@/pages/hc/ti/hcti010/index.vue'),
  '/HCTI010P01': () => import('@/pages/hc/ti/hcti010p01/index.vue'),
  '/HCTI010P02': () => import('@/pages/hc/ti/hcti010p02/index.vue'),

  // System Management - Common
  '/SYCC010': () => import('@/pages/sy/cc/sycc010/index.vue'),
  '/SYCC010P01': () => import('@/pages/sy/cc/sycc010p01/index.vue'),
  '/SYCC010P02': () => import('@/pages/sy/cc/sycc010p02/index.vue'),
  '/SYCC020': () => import('@/pages/sy/cc/sycc020/index.vue'),
  '/SYCC030': () => import('@/pages/sy/cc/sycc030/index.vue'),
  '/SYCC040': () => import('@/pages/sy/cc/sycc040/index.vue'),
  '/SYCC040P01': () => import('@/pages/sy/cc/sycc040p01/index.vue'),
  '/SYCC050': () => import('@/pages/sy/cc/sycc050/index.vue'),
  '/SYCC060': () => import('@/pages/sy/cc/sycc060/index.vue'),
  '/SYCC060P01': () => import('@/pages/sy/cc/sycc060p01/index.vue'),
  '/SYCC070': () => import('@/pages/sy/cc/sycc070/index.vue'),

  // System Management - Access Rights
  '/SYAR010': () => import('@/pages/sy/ar/syar010/index.vue'),
  '/SYAR020': () => import('@/pages/sy/ar/syar020/index.vue'),
  '/SYAR030': () => import('@/pages/sy/ar/syar030/index.vue'),
  '/SYAR030P01': () => import('@/pages/sy/ar/syar030p01/index.vue'),
  '/SYAR040': () => import('@/pages/sy/ar/syar040/index.vue'),
  '/SYAR040P01': () => import('@/pages/sy/ar/syar040p01/index.vue'),
  '/SYAR050': () => import('@/pages/sy/ar/syar050/index.vue'),
  '/SYAR060': () => import('@/pages/sy/ar/syar060/index.vue'),
  '/SYAR070': () => import('@/pages/sy/ar/syar070/index.vue'),
  '/SYAR090': () => import('@/pages/sy/ar/syar090/index.vue'),
  '/SYAR090P01': () => import('@/pages/sy/ar/syar090p01/index.vue'),

  // System Management - Log
  '/SYLG010': () => import('@/pages/sy/lg/sylg010/index.vue'),
  '/SYLG020': () => import('@/pages/sy/lg/sylg020/index.vue'),
  '/SYLG030': () => import('@/pages/sy/lg/sylg030/index.vue'),
  '/SYLG040': () => import('@/pages/sy/lg/sylg040/index.vue'),
  '/SYLG050': () => import('@/pages/sy/lg/sylg050/index.vue'),

  // System Management - Batch Job
  '/SYBJ010': () => import('@/pages/sy/bj/sybj010/index.vue'),
  '/SYBJ010P01': () => import('@/pages/sy/bj/sybj010p01/index.vue'),
  '/SYBJ010P02': () => import('@/pages/sy/bj/sybj010p02/index.vue'),
  '/SYBJ010P03': () => import('@/pages/sy/bj/sybj010p03/index.vue'),
  '/SYBJ020': () => import('@/pages/sy/bj/sybj020/index.vue'),
  '/SYBJ020P01': () => import('@/pages/sy/bj/sybj020p01/index.vue'),
  '/SYBJ030': () => import('@/pages/sy/bj/sybj030/index.vue'),

  // Master Data Management - Project
  '/MDPJ010': () => import('@/pages/md/pj/mdpj010/index.vue'),
  '/MDPJ020': () => import('@/pages/md/pj/mdpj020/index.vue'),
  '/MDPJ030': () => import('@/pages/md/pj/mdpj030/index.vue'),
  // Master Data Management - Others
  '/MDCT010': () => import('@/pages/md/ct/mdct010/index.vue'),
  '/MDCT010P01': () => import('@/pages/md/ct/mdct010p01/index.vue'),
  '/MNOD090': () => import('@/pages/mn/od/mnod090/index.vue'),
  '/MNPS010': () => import('@/pages/mn/ps/mnps010/index.vue'),
  '/MDWH010': () => import('@/pages/md/wh/mdwh010/index.vue'),
  '/MDCR010': () => import('@/pages/md/cr/mdcr010/index.vue'),
  '/MDMG010': () => import('@/pages/md/mg/mdmg010/index.vue'),
};
