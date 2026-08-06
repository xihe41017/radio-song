import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView, meta: { title: '' } },
  { path: '/request', name: 'request', component: () => import('../views/RequestView.vue'), meta: { title: '我要点歌' } },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { title: '管理员界面' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// 网页标题：当前页面 · 广播站点歌台
const SITE_TITLE = '广播站点歌台'
router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · ${SITE_TITLE}` : SITE_TITLE
})

export default router
