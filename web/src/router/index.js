//========路由配置=========
import { createRouter, createWebHistory } from 'vue-router'
import { hasPermission, isAdminArea } from '@/utils/permission'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: () => import('../views/Login.vue') },
  // 管理员路由
  {
    path: '/admin',
    component: () => import('../views/Layout.vue'),
    redirect: '/admin/dashboard',
    children: [
      { path: 'dashboard', component: () => import('../views/shared/Dashboard.vue') },
      { path: 'door', component: () => import('../views/shared/Door.vue') },
      { path: 'statistics', component: () => import('../views/shared/Statistics.vue') },
      { path: 'profile', component: () => import('../views/shared/Profile.vue') },
      { path: 'user', component: () => import('../views/admin/Users.vue'), meta: { permission: 'user.view' } },
      { path: 'device', component: () => import('../views/admin/Device.vue'), meta: { permission: 'device.view' } },
      { path: 'log', component: () => import('../views/admin/Log.vue'), meta: { permission: ['door.view_own_log', 'log.view'] } },
      { path: 'roles', component: () => import('../views/admin/RoleManage.vue'), meta: { permission: 'user.manage' } }
    ]
  },
  // 普通用户路由
  {
    path: '/user',
    component: () => import('../views/Layout.vue'),
    redirect: '/user/dashboard',
    children: [
      { path: 'dashboard', component: () => import('../views/shared/Dashboard.vue') },
      { path: 'door', component: () => import('../views/shared/Door.vue') },
      { path: 'statistics', component: () => import('../views/shared/Statistics.vue') },
      { path: 'profile', component: () => import('../views/shared/Profile.vue') }
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
  const role = localStorage.getItem('role')

  if (to.path !== '/login' && !token) {
    next('/login')
    return
  }

  // 已登录访问登录页 → 根据权限跳转
  if (to.path === '/login' && token) {
    next(isAdminArea() ? '/admin/dashboard' : '/user/dashboard')
    return
  }

  // 旧角色守卫（兼容）→ 权限不足时跳转
  if (to.meta?.roles && !to.meta.roles.includes(role)) {
    next(isAdminArea() ? '/admin/dashboard' : '/user/dashboard')
    return
  }

  // 权限守卫（支持单个权限或权限数组）
  if (to.meta?.permission) {
    const perm = to.meta.permission
    const allowed = Array.isArray(perm) ? perm.some(p => hasPermission(p)) : hasPermission(perm)
    if (!allowed) {
      next('/admin/dashboard')
      return
    }
  }

  next()
})

export default router
