//========路由配置=========
import { createRouter, createWebHistory } from 'vue-router'
import { hasPermission } from '@/utils/permission'
import { ElMessage } from 'element-plus'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: () => import('../views/Login.vue') },

  // 旧路径兼容重定向
  { path: '/admin/:pathMatch(.*)*', redirect: to => '/app' + to.path.replace('/admin', '') },
  { path: '/user/:pathMatch(.*)*', redirect: to => '/app' + to.path.replace('/user', '') },

  // 单路由树
  {
    path: '/app',
    component: () => import('../views/Layout.vue'),
    redirect: '/app/dashboard',
    children: [
      // 共享页面
      { path: 'dashboard', component: () => import('../views/shared/Dashboard.vue') },
      { path: 'door', component: () => import('../views/shared/Door.vue') },
      { path: 'statistics', component: () => import('../views/shared/Statistics.vue') },
      { path: 'profile', component: () => import('../views/shared/Profile.vue') },

      // 管理页面
      { path: 'user',   component: () => import('../views/admin/Users.vue'),    meta: { permission: 'user.view' } },
      { path: 'device', component: () => import('../views/admin/Device.vue'),  meta: { permission: 'device.view' } },
      { path: 'binding', component: () => import('../views/admin/DeviceBinding.vue'), meta: { permission: 'device.bind' } },
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

  if (to.path !== '/login' && !token) {
    next('/login')
    return
  }

  if (to.path === '/login' && token) {
    next('/app/dashboard')
    return
  }

  if (to.meta?.permission) {
    const perm = to.meta.permission
    const allowed = Array.isArray(perm) ? perm.some(p => hasPermission(p)) : hasPermission(perm)
    if (!allowed) {
      ElMessage.error('暂无权限访问该页面')
      next('/app/dashboard')
      return
    }
  }

  next()
})

export default router
