import { createRouter, createWebHistory } from 'vue-router'
import { useLessonStore } from '@/store/lessonStore'
import { useUserStore } from '@/store/userStore'

const readQueryString = (value) => {
  if (Array.isArray(value)) return value[0] || ''
  return typeof value === 'string' ? value : ''
}

const isMobileDevice = () => {
  if (typeof window === 'undefined') return false
  const ua = window.navigator.userAgent.toLowerCase()
  return /android|iphone|ipad|ipod|mobile|windows phone/.test(ua) || window.innerWidth <= 768
}

const getDefaultHomePath = (userStore) => {
  if (isMobileDevice()) return '/m/home'
  return userStore?.isTeacher ? '/pc/teacher/home' : '/pc/home'
}

const normalizeReturnUrl = (value) => {
  if (Array.isArray(value)) return normalizeReturnUrl(value[0])
  if (typeof value !== 'string') return ''
  if (!value.startsWith('/') || value.startsWith('/login')) return ''
  return value
}

const createLegacyRedirect = (path, target) => ({
  path,
  redirect: (to) => ({ path: target, query: to.query }),
})

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { shellClass: 'app-shell--auth', public: true },
  },

  // 根路径：移动设备进 /m/home，PC 进 /pc/home
  {
    path: '/',
    redirect: () => (isMobileDevice() ? '/m/home' : '/pc/home'),
  },

  // ── 移动端 ──────────────────────────────────────────────────────────
  {
    path: '/m/home',
    name: 'MobileHome',
    component: () => import('@/views-mobile/Home.vue'),
    meta: {
      shellClass: 'app-shell--mobile',
    },
  },
  {
    path: '/entry',
    name: 'PlatformEntry',
    component: () => import('@/views-mobile/PlatformEntry.vue'),
    meta: {
      shellClass: 'app-shell--mobile',
    },
  },
  {
    path: '/lesson/:lessonId',
    name: 'PluginLessonPlayer',
    component: () => import('@/views-mobile/LessonPlayer.vue'),
    meta: {
      shellClass: 'app-shell--mobile',
    },
  },
  {
    path: '/m/knowledge-map',
    name: 'MobileKnowledgeMap',
    component: () => import('@/views-mobile/KnowledgeMap.vue'),
    meta: { shellClass: 'app-shell--mobile' },
  },
  {
    path: '/m/learning-history',
    name: 'MobileLearningHistory',
    component: () => import('@/views-mobile/LearningHistory.vue'),
    meta: { shellClass: 'app-shell--mobile' },
  },
  {
    path: '/m/resources',
    name: 'MobileResources',
    component: () => import('@/views-mobile/Resources.vue'),
    meta: { shellClass: 'app-shell--mobile' },
  },
  {
    path: '/m/leaderboard',
    name: 'MobileLeaderboard',
    component: () => import('@/views-mobile/Leaderboard.vue'),
    meta: { shellClass: 'app-shell--mobile' },
  },
  {
    path: '/m/teacher/student-data',
    name: 'MobileTeacherStudentData',
    component: () => import('@/views-mobile/TeacherStudentData.vue'),
    meta: { shellClass: 'app-shell--mobile' },
  },
  {
    path: '/m/teacher/assistant',
    name: 'MobileTeacherAssistant',
    component: () => import('@/views-mobile/TeacherAIAssistant.vue'),
    meta: { shellClass: 'app-shell--mobile' },
  },
  {
    path: '/m/teacher/resources',
    name: 'MobileTeacherResources',
    component: () => import('@/views-mobile/TeacherResources.vue'),
    meta: { shellClass: 'app-shell--mobile' },
  },
  {
    path: '/m/teacher/script-editor',
    name: 'MobileScriptEditor',
    component: () => import('@/views-mobile/ScriptEditor.vue'),
    meta: { shellClass: 'app-shell--mobile' },
  },
  {
    path: '/m/:pathMatch(.*)*',
    redirect: '/m/home',
  },

  // ── PC 端 ────────────────────────────────────────────────────────────
  {
    path: '/pc',
    component: () => import('@/views/PcLayout.vue'),
    meta: { shellClass: 'app-shell--pc', platform: 'pc', requiresAuth: true },
    children: [
      { path: '', redirect: '/pc/home' },
      {
        path: 'home',
        name: 'PcHome',
        component: () => import('@/views/Home.vue'),
        meta: { label: 'Home', shellClass: 'app-shell--pc', platform: 'pc', roles: ['student'] },
      },
      {
        path: 'teacher/home',
        name: 'PcTeacherHome',
        component: () => import('@/views/TeacherHome.vue'),
        meta: { label: 'Teacher Home', shellClass: 'app-shell--pc', platform: 'pc', roles: ['teacher'] },
      },
      {
        path: 'leaderboard',
        name: 'PcLeaderboard',
        component: () => import('@/views/Leaderboard.vue'),
        meta: { label: 'Leaderboard', shellClass: 'app-shell--pc', platform: 'pc' },
      },
      {
        path: 'knowledge-graph',
        name: 'PcKnowledgeGraph',
        component: () => import('@/views/KnowledgeGraph.vue'),
        meta: { label: 'Knowledge Graph', shellClass: 'app-shell--pc', platform: 'pc' },
      },
      {
        path: 'learning-analytics',
        name: 'PcLearningAnalytics',
        component: () => import('@/views/DataFeedback.vue'),
        meta: { label: 'Learning Analytics', shellClass: 'app-shell--pc', platform: 'pc', roles: ['teacher'] },
      },
      {
        path: 'assistant',
        name: 'PcAssistant',
        component: () => import('@/views/Assistant.vue'),
        meta: { label: 'Assistant', shellClass: 'app-shell--pc', platform: 'pc' },
      },
      {
        path: 'my-courses',
        name: 'PcMyCourses',
        component: () => import('@/views/MyCourses.vue'),
        meta: { label: 'My Courses', shellClass: 'app-shell--pc', platform: 'pc', roles: ['student'] },
      },
      {
        path: 'resources',
        name: 'PcStudentResources',
        component: () => import('@/views/ResourceLibrary.vue'),
        meta: { label: 'Resources', shellClass: 'app-shell--pc', platform: 'pc', roles: ['student'] },
      },
      {
        path: 'teacher/upload',
        name: 'PcTeacherUpload',
        component: () => import('@/views/TeacherUpload.vue'),
        meta: { label: 'Teacher Upload', shellClass: 'app-shell--pc', platform: 'pc', roles: ['teacher'] },
      },
      {
        path: 'teacher/my-courses',
        name: 'PcTeacherMyCourses',
        component: () => import('@/views/TeacherMyCourses.vue'),
        meta: { label: 'Teacher My Courses', shellClass: 'app-shell--pc', platform: 'pc', roles: ['teacher'] },
      },
      {
        path: 'teacher/prep-center',
        name: 'PcTeacherPrepCenter',
        component: () => import('@/views/TeacherPrepCenter.vue'),
        meta: { label: 'Teacher Prep Center', shellClass: 'app-shell--pc', platform: 'pc', roles: ['teacher'] },
      },
      {
        path: 'teacher/script-editor',
        name: 'PcScriptEditor',
        component: () => import('@/views/ScriptEditor.vue'),
        meta: { label: 'Script Editor', shellClass: 'app-shell--pc', platform: 'pc', roles: ['teacher'] },
      },
      {
        path: 'teacher/resources',
        name: 'PcTeacherResources',
        component: () => import('@/views/ResourceLibrary.vue'),
        meta: { label: 'Teacher Resources', shellClass: 'app-shell--pc', platform: 'pc', roles: ['teacher'] },
      },
      {
        path: 'lesson/game',
        name: 'PcLessonGame',
        component: () => import('@/views/GamePlayer.vue'),
        meta: { label: 'Lesson Game', shellClass: 'app-shell--pc', platform: 'pc', roles: ['student', 'teacher'] },
      },
    ],
  },
  {
    path: '/pc/lesson/player',
    name: 'PcLessonPlayer',
    component: () => import('@/views/LessonPlayer.vue'),
    meta: { label: 'Lesson Player', shellClass: 'app-shell--pc', platform: 'pc', roles: ['student', 'teacher'] },
  },

  // ── 遗留路径兼容重定向 ───────────────────────────────────────────────
  createLegacyRedirect('/home', '/pc/home'),
  createLegacyRedirect('/teacher/home', '/pc/teacher/home'),
  createLegacyRedirect('/leaderboard', '/pc/leaderboard'),
  createLegacyRedirect('/assistant', '/pc/assistant'),
  createLegacyRedirect('/resources', '/pc/resources'),
  createLegacyRedirect('/my-courses', '/pc/my-courses'),
  createLegacyRedirect('/teacherupload', '/pc/teacher/upload'),
  createLegacyRedirect('/teacher/upload', '/pc/teacher/upload'),
  {
    path: '/teacher/script-editor',
    redirect: (to) => ({
      path: isMobileDevice() ? '/m/teacher/script-editor' : '/pc/teacher/script-editor',
      query: to.query,
    }),
  },
  createLegacyRedirect('/teacher/resources', '/pc/teacher/resources'),
  createLegacyRedirect('/teacher/data-feedback', '/pc/learning-analytics'),
  createLegacyRedirect('/lesson/player', '/pc/lesson/player'),
  createLegacyRedirect('/lesson/game', '/pc/lesson/game'),
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0, left: 0 }
  },
})

router.beforeEach((to) => {
  const userStore = useUserStore()

  const queryToken = readQueryString(to.query.token)
  if (queryToken) {
    userStore.login(
      {
        userId: readQueryString(to.query.userId) || userStore.userInfo.userId || 'platform-user',
        role: readQueryString(to.query.role) || userStore.userInfo.role || 'student',
        schoolId: readQueryString(to.query.schoolId),
      },
      queryToken,
    )
  }

  if (to.meta?.public && userStore.isLogin) {
    return normalizeReturnUrl(to.query.returnUrl) || getDefaultHomePath(userStore)
  }


  const needsAuth = to.matched.some((record) => record.meta?.requiresAuth)
    || (to.meta?.platform === 'pc' && to.path.startsWith('/pc'))

  if (needsAuth && !userStore.isLogin) {
    return {
      path: '/login',
      query: { returnUrl: to.fullPath },
    }
  }

  // 角色路由守卫（PC 端保留）
  const routeRoles = to.meta?.roles
  if (Array.isArray(routeRoles) && routeRoles.length) {
    const userRole = userStore.userInfo.role
    if (!routeRoles.includes(userRole)) {
      return getDefaultHomePath(userStore)
    }
  }

  // 同步平台上下文到 lessonStore
  const lessonStore = useLessonStore()
  lessonStore.syncPlatformContext({
    schoolId: readQueryString(to.query.schoolId),
    courseId: readQueryString(to.query.courseId),
    userId: readQueryString(to.query.userId),
    lessonId: readQueryString(to.params.lessonId || to.query.lessonId),
    role: readQueryString(to.query.role) || userStore.userInfo.role || 'student',
    token: readQueryString(to.query.token),
  })

  return true
})

export default router
