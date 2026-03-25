import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', public: true, hidden: true }
  },
  {
    path: '/weekly-report',
    redirect: '/weekly-report/members',
    meta: { public: true, hidden: true }
  },
  {
    path: '/weekly-report/team',
    name: 'PublicWeeklyReportTeam',
    component: () => import('@/views/PublicWeeklyTeamReport.vue'),
    meta: { title: '团队周报', public: true, hidden: true }
  },
  {
    path: '/weekly-report/members',
    name: 'PublicWeeklyReportMembers',
    component: () => import('@/views/PublicWeeklyMemberList.vue'),
    meta: { title: '成员周报', public: true, hidden: true }
  },
  {
    path: '/weekly-report/members/:owner',
    name: 'PublicWeeklyReportMemberDetail',
    component: () => import('@/views/PublicWeeklyMemberDetail.vue'),
    meta: { title: '成员周报详情', public: true, hidden: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘', icon: 'LayoutDashboard' }
      },
      {
        path: 'reviews',
        name: 'Reviews',
        component: () => import('@/views/Reviews.vue'),
        meta: { title: '审查记录', icon: 'FileText' }
      },
      {
        path: 'review-insights',
        name: 'ReviewInsights',
        component: () => import('@/views/ReviewInsights.vue'),
        meta: { title: '问题分析', icon: 'BarChart3' }
      },
      {
        path: 'weekly-feedback-report',
        name: 'WeeklyFeedbackReport',
        component: () => import('@/views/WeeklyFeedbackReport.vue'),
        meta: { title: '团队周报', icon: 'CalendarRange', public: true }
      },
      {
        path: 'reviews/:id',
        name: 'ReviewDetail',
        component: () => import('@/views/ReviewDetail.vue'),
        meta: { title: '审查详情', hidden: true }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/Projects.vue'),
        meta: { title: '项目管理', icon: 'FolderKanban' }
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/ProjectDetail.vue'),
        meta: { title: '项目详情', hidden: true }
      },
      {
        path: 'config',
        name: 'Config',
        component: () => import('@/views/Config.vue'),
        meta: { title: '配置管理', icon: 'Settings' }
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/Logs.vue'),
        meta: { title: '日志监控', icon: 'ScrollText' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!auth.hydrated) auth.hydrate()

  const isPublicRoute = to.matched.some((record) => Boolean(record.meta?.public))
  const isAuthenticated = auth.isAuthenticated
  if (!isAuthenticated && !isPublicRoute) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (isAuthenticated && to.path === '/login') {
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : '/dashboard'
    if (redirect.startsWith('/') && !redirect.startsWith('//')) return redirect
    return '/dashboard'
  }

  return true
})

export default router
