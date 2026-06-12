import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from "@/views/LoginPage.vue";
import MainPage from "@/views/MainPage.vue";
import CoursePage from "@/views/CoursePage.vue";
import MyAcademyPage from "@/views/MyAcademy/MyAcademyPage.vue";
import Course from "@/views/MyAcademy/Assignment/Course.vue";
import Attendance from "@/views/MyAcademy/Assignment/Attendance.vue";
import MyCoursePage from "@/views/MyAcademy/MyCoursePage.vue";
import EmotionRecord from "@/components/UseCenterPage/EmotionRecord.vue";
import UserCenterPage from "@/views/UserCenterPage.vue";
import TeacherPortal from "@/views/TeachingPortal.vue";
import StudentPortal from "@/views/StudentPortal.vue";
import StudentDemoPage from "@/views/StudentDemoPage.vue";
import NotFoundPage from "@/views/InfoPage/NotFoundPage.vue";
import GoToLearning from "@/components/MyAcademyPage/GoToLearning.vue";
import LearningProgress from "@/components/MyAcademyPage/LearningProgress.vue";
import ProblemHistory from "@/components/MyAcademyPage/ProblemHistory.vue";
import AIEvaluation from "@/components/MyAcademyPage/AIEvaluation.vue";
import ChatView from "@/components/MyAcademyPage/ChatView.vue";
import DevelopingPage from "@/components/MyAcademyPage/DevelopingPage.vue";

import {useAuth} from "@/assets/static/js/useAuth"
import TeachOverview from "@/views/TeachingPortal/TeachOverview.vue";
import ProblemPage from "@/views/MyAcademy/ProblemPage.vue";
import CourseCreate from "@/views/TeachingPortal/CourseManagement/CourseCreate.vue";
import StudentOverview from "@/views/TeachingPortal/StudentManagement/StudentOverview.vue";
import StudentInfo from "@/views/TeachingPortal/StudentManagement/StudentInfo.vue";
import ParentPage from "@/views/ParentPage.vue";
import NoticePage from "@/views/NoticePage.vue";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
      {path:"/", redirect: "/login"},
    {path: "/login", component: LoginPage, meta: {requiresAuth: false}},
    {
      path: "/portal",
      component: StudentPortal,
      meta: { requiresAuth: true, role: "student" },
      children: [
        { path: "", redirect: "/portal/home" },
        { path: "home", component: MainPage, meta: { requiresAuth: true, role: "student", label: "首页" } },
        { path: "assistant/qa", component: ChatView, meta: { requiresAuth: true, role: "student" }, props: { title: '智能问答', placeholder: '请输入你的问题...' } },
        { path: "assistant/resources", component: ChatView, meta: { requiresAuth: true, role: "student" }, props: { title: '资源推荐', placeholder: '告诉我你想学什么，我来推荐资源...' } },
        { path: "assistant/images", component: ChatView, meta: { requiresAuth: true, role: "student" }, props: { title: '图片生成', placeholder: '描述你想要的图片内容...' } },
        { path: "learning", component: GoToLearning, meta: { requiresAuth: true, role: "student", label: "前往学习" } },
        { path: "progress", component: LearningProgress, meta: { requiresAuth: true, role: "student", label: "学习进度" } },
        { path: "history", component: ProblemHistory, meta: { requiresAuth: true, role: "student", label: "做题历史" } },
        { path: "graph", component: DevelopingPage, meta: { requiresAuth: true, role: "student", label: "知识图谱" }, props: { title: '知识图谱' } },
        { path: "evaluation", component: AIEvaluation, meta: { requiresAuth: true, role: "student", label: "AI评估" } },
        { path: "emotion", component: EmotionRecord, meta: { requiresAuth: true, role: "student", label: "情绪记录" } },
        { path: "courses/my", component: MyAcademyPage, meta: { requiresAuth: true, role: "student", label: "我的课程" } },
        { path: "courses/public", component: MainPage, meta: { requiresAuth: true, role: "student", label: "公共课程" } },
        { path: "knowledge", component: StudentDemoPage, meta: { requiresAuth: true, role: "student", label: "知识库", description: "课程资料和知识库管理入口。当前是本地演示页面。" } },
      ],
    },
    { path:"/course/:id", component:CoursePage, meta: {requiresAuth: false}},

    {path:"/404", component: NotFoundPage, meta: {requiresAuth: false}},

    {path:"/user/my-course/:id", component:MyCoursePage, meta: {requiresAuth: true, role: "student"}},
    {path:"/user/", redirect: "/portal/emotion"},
    {path:"/academy", redirect: "/portal/traces"},
      {path:"/academy/problem/:id", component:ProblemPage, meta: {requiresAuth: true, role: "student"}},
    {path:"/teaching",
        component: TeacherPortal,
        meta: {requiresAuth: true, role: "teacher"},
        children: [
            {
                path: 'portal',
                component: TeachOverview,
                meta: {requiresAuth: true, role: "teacher"},
            },
            {
                path: 'course',
                meta: {requiresAuth: true, role: "teacher"},
                children:[
                    {
                        path: 'create',
                        component: CourseCreate,
                        meta: {requiresAuth: true, role: "teacher"},
                    }
                ]
            },
            {
                path: 'student',
                meta: {requiresAuth: true, role: "teacher"},
                children:[
                    {
                        path: 'overview',
                        component: StudentOverview,
                        meta: {requiresAuth: true, role: "teacher"},
                    },
                    {
                        path: 'info/:id',
                        component: StudentInfo,
                        meta: {requiresAuth: true, role: "teacher"},
                    }
                ]
            }
        ]
    },
      {path: "/parent", component: ParentPage, meta: {requiresAuth: true, role: "parent"}},
      {path: "/notice", component: NoticePage, meta: {requiresAuth: true, role: "parent"}},
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
    if (to.matched.length === 0) {
        next('/404'); // 重定向到404页面的路径
    }
    else{
        if (to.meta.requiresAuth) {
            const {isAuthenticated, user} = useAuth()
            if (!isAuthenticated.value || !user.value) {
                next({path: "/login"})
            } else {
                if (to.meta.role && user.value.role !== to.meta.role) {
                    if (user.value.role === "teacher") {
                        next({path: "/teaching/portal"})
                    } else if (user.value.role === "parent") {
                        next({path: "/parent"})
                    } else {
                        next({path: "/portal"})
                    }
                } else {
                    next()
                }
            }
        } else {
            next()
        }
    }
})

export default router
