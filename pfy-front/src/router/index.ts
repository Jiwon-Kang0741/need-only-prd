import { createRouter, createWebHistory } from 'vue-router';

import { showNoAuthToast } from '@/utils/errorHandler';

import { staticRoutes } from './staticRoutes';

export const router = createRouter({
  history: createWebHistory('/'),
  routes: staticRoutes,
});

router.beforeEach((to) => {
  const exists = router.getRoutes().some((r) => r.path === to.path);
  if (!exists) {
    setTimeout(() => {
      showNoAuthToast();
    });
    return false;
  }
  return true;
});
