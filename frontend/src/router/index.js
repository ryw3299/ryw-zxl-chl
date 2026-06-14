import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/userStore'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { public: true },
  },
  {
    path: '/dashboard',
    component: () => import('@/components/PageLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
    ],
  },
  {
    path: '/profile',
    component: () => import('@/components/PageLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Profile', component: () => import('@/views/ProfilePage.vue') },
      { path: 'init', name: 'ProfileInit', component: () => import('@/views/ProfileInit.vue') },
    ],
  },
  {
    path: '/settings',
    component: () => import('@/components/PageLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Settings', component: () => import('@/views/SettingsPage.vue') },
    ],
  },
  {
    path: '/wrong-book',
    redirect: '/learning-path/wrong-book',
  },
  {
    path: '/learning-path',
    component: () => import('@/components/PageLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'LearningPath', component: () => import('@/views/LearningPath.vue') },
      { path: 'wrong-book', name: 'WrongBook', component: () => import('@/views/WrongBookPage.vue') },
      { path: 'favorites', name: 'Favorites', component: () => import('@/views/FavoritesPage.vue') },
    ],
  },
  {
    path: '/resources',
    component: () => import('@/components/PageLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'ResourceCenter', component: () => import('@/views/ResourceCenter.vue') },
      { path: ':id', name: 'ResourceDetail', component: () => import('@/views/ResourceDetail.vue') },
      { path: ':id/read', name: 'DocumentReader', component: () => import('@/views/DocumentReader.vue') },
      { path: ':id/video', name: 'VideoLearning', component: () => import('@/views/VideoLearningPage.vue') },
      { path: ':id/quiz', name: 'QuizPractice', component: () => import('@/views/QuizPracticePage.vue') },
    ],
  },
  {
    path: '/generated-resources',
    component: () => import('@/components/PageLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'GeneratedResource', component: () => import('@/views/GeneratedResource.vue') },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/components/PageLayout.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
    children: [
      { path: '', name: 'Admin', component: () => import('@/views/AdminPage.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const isLoggedIn = userStore.isLogin

  if (to.meta.public) {
    next()
    return
  }

  if (to.meta.requiresAuth && !isLoggedIn) {
    next({ name: 'Login', query: { returnUrl: to.fullPath } })
    return
  }

  // Role check
  const roles = to.meta.roles
  if (roles && !roles.includes(userStore.user?.role)) {
    next({ name: 'Dashboard' })
    return
  }

  next()
})

export default router
