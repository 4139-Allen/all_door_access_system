//========路由配置=========
import { createRouter, createWebHistory } from 'vue-router'
import { hasPermission } from '@/utils/permission'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: () => import('../views/Login.vue') },

  // 旧路径兼容重定向（保留书签/链接兼容性）
  { path: '/admin/:pathMatch(.*)*', redirect: to => '/app' + to.path.replace('/admin', '') },
  { path: '/user/:pathMatch(.*)*', redirect: to => '/app' + to.path.replace('/user', '') },

  // 统一 /app 单路由树
  {
    path: '/app',
    component: () => import('../views/Layout.vue'),
    redirect: '/app/dashboard',
    children: [
      // 共享页面（无需特定权限，内容按权限动态展示）
      { path: 'dashboard', component: () => import('../views/shared/Dashboard.vue') },
      { path: 'door', component: () => import('../views/shared/Door.vue') },
      { path: 'statistics', component: () => import('../views/shared/Statistics.vue') },
      { path: 'profile', component: () => import('../views/shared/Profile.vue') },

      // 管理页面（需要特定权限）
      { path: 'user',   component: () => import('../views/admin/Users.vue'),    meta: { permission: 'user.view' } },
      { path: 'device', component: () => import('../views/admin/Device.vue'),  meta: { permission: 'device.view' } },
      { path: 'log',    component: () => import('../views/admin/Log.vue'),     meta: { permission: ['door.view_own_log', 'log.view'] } },
      { path: 'alert',  component: () => import('../views/admin/Alert.vue'),   meta: { permission: 'alert.view' } },
      { path: 'roles',  component: () => import('../views/admin/RoleManage.vue'), meta: { permission: 'user.manage' } },
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/NotFound.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  // 未登录 → 登录页
  if (to.path !== '/login' && !token) {
    next('/login')
    return
  }

  // 已登录访问登录页 → 仪表盘
  if (to.path === '/login' && token) {
    next('/app/dashboard')
    return
  }

  // 权限守卫（支持单个权限或权限数组）
  if (to.meta?.permission) {
    const perm = to.meta.permission
    const allowed = Array.isArray(perm) ? perm.some(p => hasPermission(p)) : hasPermission(perm)
    if (!allowed) {
      next('/app/dashboard')
      return
    }
  }

  next()
})

export default router
