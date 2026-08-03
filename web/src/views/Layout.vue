<template>
  <el-container class="layout-container">
    <!-- 桌面端侧边栏 -->
    <SidebarMenu :role="role" class="desktop-sidebar" />

    <!-- 移动端侧边栏 Overlay -->
    <Teleport to="body">
      <Transition name="sidebar-fade">
        <div v-if="sidebarOpen" class="mobile-sidebar-overlay" @click="sidebarOpen = false">
          <div class="mobile-sidebar-panel" @click.stop>
            <SidebarMenu :role="role" @navigate="sidebarOpen = false" />
          </div>
        </div>
      </Transition>
    </Teleport>

    <el-container class="main-container">
      <!-- 路由加载进度条 -->
      <div v-if="routeLoading" class="route-progress">
        <div class="route-progress-bar"></div>
      </div>

      <!-- 顶部栏 -->
      <el-header class="app-header">
        <div class="header-left">
          <el-button text class="hamburger-btn" @click="sidebarOpen = true">
            <el-icon :size="20"><Fold /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/app/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentPageName }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-tooltip content="刷新权限" placement="bottom" :show-after="300">
            <el-button text class="refresh-btn" :loading="refreshing" @click="handleRefreshPermission">
              <el-icon :size="16"><Refresh /></el-icon>
            </el-button>
          </el-tooltip>
          <el-button text class="logout-btn" @click="logout">
            <el-icon :size="16"><SwitchButton /></el-icon>
            <span>退出登录</span>
          </el-button>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main class="app-main">
        <router-view v-slot="{ Component, route }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>

</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ref, computed, watch } from 'vue'
import { Fold, SwitchButton, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { refreshPermissions } from '@/utils/refreshPermissions'
import { closeWebSocket } from '@/services/websocket'
import { startRelativeTimeTick } from '@/utils/formatTime'

startRelativeTimeTick()
import SidebarMenu from '@/components/Layout/SidebarMenu.vue'

const router = useRouter()
const route = useRoute()
const role = ref(localStorage.getItem('role') || '')
const sidebarOpen = ref(false)
const routeLoading = ref(false)

// 路由切换时显示加载进度条
let loadingTimer = null
router.beforeEach(() => {
  loadingTimer = setTimeout(() => { routeLoading.value = true }, 100)
})
router.afterEach(() => {
  clearTimeout(loadingTimer)
  setTimeout(() => { routeLoading.value = false }, 200)
  sidebarOpen.value = false
})

const pageNames = {
  '/app/dashboard': '仪表盘',
  '/app/door': '用户开门',
  '/app/statistics': '数据统计',
  '/app/profile': '个人中心',
  '/app/user': '用户管理',
  '/app/device': '设备管理',
  '/app/log': '门禁日志',
  '/app/alert': '异常事件',
  '/app/roles': '权限管理',
}

const currentPageName = computed(() => pageNames[route.path] || '')

// 手动刷新当前用户权限（所有角色可用；菜单/按钮显隐读 localStorage，刷新后需重载页面生效）
const refreshing = ref(false)
const handleRefreshPermission = async () => {
  refreshing.value = true
  const perms = await refreshPermissions()
  refreshing.value = false
  if (perms !== null) {
    ElMessage.success('权限已刷新')
    // localStorage 非响应式，重新加载以应用最新的菜单/按钮显隐
    setTimeout(() => location.reload(), 600)
  } else {
    ElMessage.error('权限刷新失败，请稍后重试')
  }
}

const logout = async () => {
  try {
    await ElMessageBox.confirm('确认退出登录？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  closeWebSocket()
  try {
    await request.post('/auth/logout')
  } catch {
    // 忽略退出登录的接口错误
  }
  localStorage.clear()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  min-height: 100vh;
  background: #f1f5f9;
}

.desktop-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  flex-shrink: 0;
}

.main-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

/* ======== 顶部栏 ======== */
.app-header {
  height: 56px !important;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 28px !important;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-left :deep(.el-breadcrumb__inner) {
  font-size: 14px;
}

.header-left :deep(.el-breadcrumb__inner.is-link) {
  color: #64748b;
  font-weight: 400;
}

.header-left :deep(.el-breadcrumb__inner.is-link:hover) {
  color: #6366f1;
}

.header-left :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #1e293b;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.refresh-btn {
  color: #909399;
  padding: 8px;
}

.refresh-btn:hover {
  color: #6366f1;
}

.logout-btn {
  color: #909399;
  font-size: 13px;
  gap: 4px;
}

.logout-btn:hover {
  color: #f56c6c;
}

/* ======== 主内容 ======== */
.app-main {
  background: #f1f5f9;
  padding: 20px 24px;
  min-height: calc(100vh - 56px);
}

/* ======== 路由加载进度条 ======== */
.route-progress {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  z-index: 9999;
  overflow: hidden;
}
.route-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #818cf8, #6366f1);
  background-size: 200% 100%;
  animation: progress-slide 1.2s ease-in-out infinite;
  border-radius: 0 2px 2px 0;
}
@keyframes progress-slide {
  0% { width: 0%; transform: translateX(0); }
  50% { width: 70%; }
  100% { width: 100%; transform: translateX(0); }
}

/* ======== 页面过渡动画 ======== */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

/* ======== 移动端适配 ======== */
.hamburger-btn {
  display: none;
  padding: 6px;
  margin-right: 8px;
}

/* 移动端侧边栏 Overlay */
.mobile-sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.4);
}

.mobile-sidebar-panel {
  position: absolute;
  left: 0;
  top: 0;
  width: 220px;
  height: 100%;
}

/* Overlay 动画 */
.sidebar-fade-enter-active,
.sidebar-fade-leave-active {
  transition: opacity 0.25s ease;
}
.sidebar-fade-enter-active .mobile-sidebar-panel,
.sidebar-fade-leave-active .mobile-sidebar-panel {
  transition: transform 0.25s ease;
}
.sidebar-fade-enter-from,
.sidebar-fade-leave-to {
  opacity: 0;
}
.sidebar-fade-enter-from .mobile-sidebar-panel,
.sidebar-fade-leave-to .mobile-sidebar-panel {
  transform: translateX(-100%);
}

@media (max-width: 768px) {
  .desktop-sidebar {
    display: none;
  }
  .mobile-sidebar-overlay {
    display: flex;
  }
  .hamburger-btn {
    display: flex;
  }
  .app-header {
    padding: 0 16px !important;
  }
  .app-main {
    padding: 12px;
  }
}
</style>
