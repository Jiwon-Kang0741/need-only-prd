import { createRouter, createWebHistory } from 'vue-router';

import { staticRoutes } from './staticRoutes';

export const router = createRouter({
  history: createWebHistory('/'),
  routes: staticRoutes,
});

// need-only-prd Mockup 런타임: 존재하지 않는 경로도 차단하지 않고 NotFound 라우트로 fallback.
// (원본 가드는 navigation을 abort시켜 bootstrap이 중단되는 문제가 있어 제거)
router.beforeEach(() => true);
