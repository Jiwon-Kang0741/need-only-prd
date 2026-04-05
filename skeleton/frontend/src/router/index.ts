import { createRouter, createWebHistory } from 'vue-router'

// Router will be dynamically configured when generated pages are added
const routes = [
  {
    path: '/',
    component: () => import('@/App.vue'),
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
