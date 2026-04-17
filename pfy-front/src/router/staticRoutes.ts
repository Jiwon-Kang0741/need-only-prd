import type { RouteRecordRaw } from 'vue-router';

const popupRoutes: RouteRecordRaw[] = [
  {
    path: '/popup/:popupId',
    component: () => import('@/pages/popup/features/PopupView.vue'),
    children: [
      {
        path: '',
        name: 'popupDynamic',
        component: () =>
          import('@/pages/popup/features/DynamicPopupLoader.vue'),
      },
    ],
  },
];

export const staticRoutes: RouteRecordRaw[] = [
  {
    path: '/auth',
    component: () => import('@/pages/auth/index.vue'),
    children: [
      {
        path: 'login',
        name: 'Login',
        component: () => import('@/pages/auth/login/index.vue'),
      },
      {
        path: 'otp',
        name: 'Otp',
        component: () => import('@/pages/auth/otp/index.vue'),
      },
      {
        path: 'forgot-password',
        name: 'ForgotPassword',
        component: () => import('@/pages/auth/forgot-password/index.vue'),
      },
      {
        path: 'reset-password',
        name: 'ResetPassword',
        component: () => import('@/pages/auth/reset-password/index.vue'),
      },
      {
        path: 'link-sent',
        name: 'LinkSent',
        component: () => import('@/pages/auth/link-sent/index.vue'),
      },
      {
        path: 'password-changed',
        name: 'PasswordChanged',
        component: () => import('@/pages/auth/password-changed/index.vue'),
      },
    ],
  },
  ...popupRoutes,
  {
    path: '/guide',
    name: 'Guide',
    component: () => import('@/pages/guide/Index.vue'),
  },
  // ──────────────────────────────────────────────────────────────────────────
  // 템플릿 미리보기 라우트 (로그인 없이 접근 가능 - 개발/검토 용도)
  // 사용법: pnpm dev 실행 후 아래 URL로 접근
  //   http://localhost:5173/template-a  →  Type A (Standard Search)
  //   http://localhost:5173/template-b  →  Type B (Input Detail)
  //   http://localhost:5173/template-c  →  Type C (Tree-Grid)
  //   http://localhost:5173/template-d  →  Type D (Master-Detail)
  // ──────────────────────────────────────────────────────────────────────────
  {
    path: '/template-a',
    name: 'TemplateA',
    meta: { menuId: 'TEMPLATE_A' },
    component: () => import('@/templates/TypeA_StandardSearch/index.vue'),
  },
  {
    path: '/template-b',
    name: 'TemplateB',
    meta: { menuId: 'TEMPLATE_B' },
    component: () => import('@/templates/TypeB_InputDetail/index.vue'),
  },
  {
    path: '/template-c',
    name: 'TemplateC',
    meta: { menuId: 'TEMPLATE_C' },
    component: () => import('@/templates/TypeC_TreeGrid/index.vue'),
  },
  {
    path: '/template-d',
    name: 'TemplateD',
    meta: { menuId: 'TEMPLATE_D' },
    component: () => import('@/templates/TypeD_MasterDetail/index.vue'),
  },
  // ──────────────────────────────────────────────────────────────────────────
  // Mockup 미리보기 라우트 (로그인 없이 접근 가능 - 고객 시연/검토 용도)
  // ──────────────────────────────────────────────────────────────────────────
  {
    path: '/mockup/builder',
    name: 'MockupBuilder',
    component: () => import('@/pages/mockup/MockupBuilder.vue'),
  },
    {
        path: '/MNET010',
        name: 'MNET010',
        meta: { menuId: 'MNET010', generated: true },
        component: () => import('@/pages/generated/mnet010/index.vue'),
      },
    {
      path: '/USER_ACCS_LIST',
      name: 'USER_ACCS_LIST',
      meta: { menuId: 'USER_ACCS_LIST', generated: true },
      component: () => import('@/pages/generated/user_accs_list/index.vue'),
    },
    {
        path: '/generated/UserAccessList',
        name: 'generated-UserAccessList',
        meta: { generated: true },
        component: () => import('@/pages/generated/UserAccessList.vue'),
      },
    {
        path: '/generated/FraudReport',
        name: 'generated-FraudReport',
        meta: { generated: true },
        component: () => import('@/pages/generated/FraudReport.vue'),
      },
    {
        path: '/generated/UserAccessLogList',
        name: 'generated-UserAccessLogList',
        meta: { generated: true },
        component: () => import('@/pages/generated/UserAccessLogList.vue'),
      },
    {
        path: '/generated/UserList',
        name: 'generated-UserList',
        meta: { generated: true },
        component: () => import('@/pages/generated/UserList.vue'),
      },
    {
        path: '/generated/EduProgList',
        name: 'generated-EduProgList',
        meta: { generated: true },
        component: () => import('@/pages/generated/EduProgList.vue'),
      },
    {
      path: '/SCR001',
      name: 'SCR001',
      meta: { menuId: 'SCR001', generated: true },
      component: () => import('@/pages/generated/scr001/index.vue'),
    },
    {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/pages/_system/notFound/index.vue'),
  },
];
