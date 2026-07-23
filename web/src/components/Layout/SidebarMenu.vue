<template>
  <el-aside width="220px" class="sidebar-container">
    <!-- Logo -->
    <div class="sidebar-header">
      <div class="logo-mark">
        <img src="/favicon-v3.svg" alt="Logo" class="logo-icon" />
      </div>
      <div class="logo-text">
        <span class="logo-title">智能门禁</span>
        <span class="logo-sub">管理控制系统</span>
      </div>
    </div>

    <!-- 导航 -->
    <el-menu
      :default-active="activeRoute"
      background-color="transparent"
      text-color="#606266"
      active-text-color="#409eff"
      router
      class="sidebar-menu"
      @select="emit('navigate')"
    >
      <div class="menu-label">导航</div>

      <el-menu-item :index="routePrefix + '/dashboard'">
        <el-icon><HomeFilled /></el-icon>
        <span>首页</span>
      </el-menu-item>

      <el-menu-item :index="routePrefix + '/door'">
        <el-icon><Key /></el-icon>
        <span>用户开门</span>
      </el-menu-item>

      <el-menu-item :index="routePrefix + '/statistics'">
        <el-icon><DataLine /></el-icon>
        <span>数据统计</span>
      </el-menu-item>

      <template v-if="hasPermission('device.view') || hasPermission('log.view') || hasPermission('alert.view')">
        <div class="menu-label">管理</div>

        <el-menu-item v-if="hasPermission('device.view')" :index="routePrefix + '/device'">
          <el-icon><Lock /></el-icon>
          <span>设备管理</span>
        </el-menu-item>

        <el-menu-item v-if="hasPermission('log.view')" :index="routePrefix + '/log'">
          <el-icon><List /></el-icon>
          <span>门禁日志</span>
        </el-menu-item>

        <el-menu-item v-if="hasPermission('alert.view')" :index="routePrefix + '/alert'">
          <el-icon><Warning /></el-icon>
          <span>异常事件</span>
        </el-menu-item>
      </template>

      <template v-if="hasPermission('user.view')">
        <div class="menu-label">系统</div>

        <el-menu-item :index="routePrefix + '/user'">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </el-menu-item>

        <el-menu-item v-if="hasPermission('user.manage')" :index="routePrefix + '/roles'">
          <el-icon><Setting /></el-icon>
          <span>权限管理</span>
        </el-menu-item>
      </template>
    </el-menu>

    <!-- 底部 -->
    <router-link :to="routePrefix + '/profile'" class="sidebar-footer">
      <div class="user-info">
        <div class="user-avatar">
          <img v-if="avatar" :src="avatar" class="user-avatar-img" @error="avatar = ''" />
          <span v-else class="user-avatar-fallback">{{ username.charAt(0).toUpperCase() }}</span>
        </div>
        <div class="user-meta">
          <span class="user-name">{{ username }}</span>
          <span class="user-role">{{ roleName }}</span>
        </div>
        <el-icon class="user-arrow"><ArrowRight /></el-icon>
      </div>
    </router-link>
  </el-aside>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowRight, Lock, HomeFilled, Key, DataLine, UserFilled, List, Setting, Warning } from '@element-plus/icons-vue'
import { hasPermission } from '@/utils/permission'

defineProps({ role: String })
const emit = defineEmits(['navigate'])
const route = useRoute()
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const username = computed(() => localStorage.getItem('username') || '用户')
const roleName = computed(() => localStorage.getItem('role_name') || '用户')

const resolveAvatar = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return API_BASE + path
}
const avatar = ref(resolveAvatar(localStorage.getItem('avatar') || ''))

const onAvatarUpdated = () => {
  avatar.value = resolveAvatar(localStorage.getItem('avatar') || '')
}
onMounted(() => window.addEventListener('avatar-updated', onAvatarUpdated))
onUnmounted(() => window.removeEventListener('avatar-updated', onAvatarUpdated))
// 统一 /app 路由前缀（单路由树，根据权限控制菜单显隐）
const routePrefix = '/app'
const activeRoute = computed(() => route.path)
</script>

<style scoped>
.sidebar-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #fff;
  border-right: 1px solid #ebeef5;
  user-select: none;
}

/* ======== Logo ======== */
.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px 20px;
  border-bottom: 1px solid #f0f2f5;
}

.logo-mark {
  width: 36px;
  height: 36px;
  background: #000000;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.logo-icon {
  width: 28px;
  height: 28px;
}

.logo-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.logo-title {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
  letter-spacing: 0.5px;
  line-height: 1.3;
}

.logo-sub {
  font-size: 11px;
  color: #909399;
  line-height: 1.3;
}

/* ======== 菜单 ======== */
.sidebar-menu {
  flex: 1;
  border-right: none;
  padding: 8px 12px;
  overflow-y: auto;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 100%;
}

.menu-label {
  padding: 20px 12px 6px;
  font-size: 11px;
  font-weight: 600;
  color: #c0c4cc;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.el-menu-item {
  border-radius: 6px;
  margin: 2px 0;
  height: 40px !important;
  line-height: 40px !important;
  padding: 0 12px !important;
  font-size: 14px;
}

.el-menu-item:hover {
  background: #f5f7fa !important;
  color: #303133 !important;
}

.el-menu-item.is-active {
  background: #ecf5ff !important;
  color: #409eff !important;
}

/* ======== 底部 ======== */
.sidebar-footer {
  display: block;
  padding: 16px 20px;
  border-top: 1px solid #f0f2f5;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.2s;
  border-radius: 0;
}

.sidebar-footer:hover {
  background: #f5f7fa;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-arrow {
  margin-left: auto;
  font-size: 12px;
  color: #c0c4cc;
  transition: color 0.2s, transform 0.2s;
}

.sidebar-footer:hover .user-arrow {
  color: #909399;
  transform: translateX(2px);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #6366f1;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}

.user-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  line-height: 1.3;
}

.user-role {
  font-size: 11px;
  color: #909399;
  line-height: 1.3;
}

/* 滚动条 */
.sidebar-menu::-webkit-scrollbar {
  width: 4px;
}

.sidebar-menu::-webkit-scrollbar-thumb {
  background: #e4e7ed;
  border-radius: 2px;
}
</style>
