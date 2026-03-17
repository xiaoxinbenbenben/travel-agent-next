import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('@/views/Home.vue')
    },
    {
      path: '/result',
      name: 'Result',
      component: () => import('@/views/Result.vue')
    }
  ],
  scrollBehavior() {
    return {
      top: 0
    }
  }
})

export default router
