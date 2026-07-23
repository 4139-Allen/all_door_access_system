<template>
  <div class="dashboard">
    <!-- 欢迎横幅 -->
    <el-card class="welcome-banner" shadow="never">
      <div class="welcome-content">
        <div class="welcome-left">
          <div class="greeting-line">
            <span class="greeting-text">{{ greetingText }}，</span>
            <span class="greeting-role">{{ roleLabel }}</span>
          </div>
          <p class="welcome-sub">{{ todaySub }}</p>
        </div>
        <div class="welcome-right">
          <div class="date-text">{{ dateStr }}</div>
          <div class="time-text">{{ timeStr }}</div>
        </div>
      </div>
    </el-card>

    <!-- 统计 -->
    <StatSkeleton v-if="statLoading" :count="hasPermission('user.view') ? 4 : 3" />
    <el-row v-else :gutter="20" class="stat-row">
      <StatCard
        v-if="hasPermission('user.view')"
        title="用户总数"
        :number="stat.user_total"
        color="#409eff"
        :icon="UserFilled"
      />
      <StatCard
        title="在线设备"
        :number="stat.device_online"
        color="#22c55e"
        :icon="Monitor"
      />
      <StatCard
        title="离线设备"
        :number="stat.device_offline"
        color="#909399"
        :icon="WarningFilled"
      />
      <StatCard
        :title="hasPermission('log.view') ? '今日开门记录' : '我的今日开门记录'"
        :number="stat.today_log"
        color="#e6a23c"
        :icon="Key"
      />
    </el-row>

    <!-- 快捷操作 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <span class="section-title">快捷操作</span>
      </template>
      <div class="quick-actions">
        <el-button v-if="hasPermission('door.open')" class="action-btn" @click="goRoute(routePrefix + '/door')">
          <el-icon><Key /></el-icon>快速开门
        </el-button>
        <el-button class="action-btn" @click="goRoute(routePrefix + '/statistics')">
          <el-icon><DataLine /></el-icon>数据统计
        </el-button>
        <el-button v-if="hasPermission('device.view')" class="action-btn" @click="goRoute(routePrefix + '/device')">
          <el-icon><Monitor /></el-icon>设备管理
        </el-button>
        <el-button v-if="hasPermission('log.view')" class="action-btn" @click="goRoute(routePrefix + '/log')">
          <el-icon><List /></el-icon>查看日志
        </el-button>
        <el-button v-if="hasPermission('user.manage')" class="action-btn" @click="goRoute(routePrefix + '/user')">
          <el-icon><UserFilled /></el-icon>用户管理
        </el-button>
      </div>
    </el-card>

    <!-- 实时事件流 -->
    <el-card class="section-card" shadow="never">
      <template #header>
        <div class="section-header">
          <span class="section-title">实时事件流</span>
          <el-tag v-if="eventList.length > 0" type="success" size="small" effect="plain">
            共 {{ eventList.length }} 条
          </el-tag>
        </div>
      </template>
      <div class="event-stream" v-loading="logsLoading">
        <TransitionGroup name="event-slide" tag="div">
          <div
            v-for="event in displayedEvents"
            :key="event.id"
            class="event-item"
          >
            <div class="event-dot"></div>
            <div class="event-body">
              <div class="event-main">
                <span class="event-user">{{ event.username }}</span>
                <span class="event-sep">{{ getActionVerb(event.action) }}</span>
                <span class="event-device">{{ event.device_name }}</span>
                <span v-if="event.location" class="event-location">({{ event.location }})</span>
              </div>
              <div class="event-meta">
                <el-tag size="small" :type="getActionTagType(event.action)" effect="plain">
                  {{ event.action }}
                </el-tag>
                <el-tooltip :content="event.status" placement="top" :show-after="300">
                  <el-tag size="small" :type="event.status === '成功' ? 'success' : 'danger'" effect="light">
                    {{ getShortStatus(event.status) }}
                  </el-tag>
                </el-tooltip>
                <el-tooltip :content="event.timestamp" placement="top" :show-after="300">
                  <span class="event-time">{{ getRelativeTime(event.timestamp) }}</span>
                </el-tooltip>
              </div>
            </div>
          </div>
        </TransitionGroup>
        <div v-if="displayedEvents.length === 0 && !logsLoading" class="event-empty">
          <svg class="event-empty-icon" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="32" cy="32" r="24" stroke="#cbd5e1" stroke-width="2"/>
            <polyline points="26,32 30,36 38,28" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>暂无事件</span>
        </div>
      </div>
    </el-card>

    <!-- AI 悬浮按钮 -->
    <div v-if="hasPermission('door.open') || hasPermission('device.view')" class="ai-fab-wrap" @click="aiDialog = true">
      <button class="ai-fab">AI</button>
    </div>

    <AiChatBox v-model:visible="aiDialog" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UserFilled, Monitor, WarningFilled, Key, DataLine, List } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { hasPermission } from '@/utils/permission'
import { getActionTagType, getShortStatus } from '@/utils/format'
import StatCard from '@/components/Dashboard/StatCard.vue'
import StatSkeleton from '@/components/common/StatSkeleton.vue'
import AiChatBox from '@/components/Dashboard/AiChatBox.vue'
import { useDoorEventStream } from '@/composables/useDoorEventStream'
import { useDeviceStatus } from '@/composables/useDeviceStatus'

const router = useRouter()
const role = ref(localStorage.getItem('role') || '')
const aiDialog = ref(false)
const logsLoading = ref(false)

const routePrefix = '/user'

const statLoading = ref(true)
const stat = ref({ user_total: 0, device_online: 0, device_offline: 0, today_log: 0 })
const { deviceStatusMap } = useDeviceStatus()
// 记录上次设备状态，用于计算差值
const devicePrevStatus = {}
const recentLogs = ref([])
const { eventList, addDoorEvent, getRelativeTime } = useDoorEventStream()
const displayedEvents = computed(() => eventList.slice(0, 20))
// 标记是否还在初始化阶段（初始加载的历史事件不计入 today_log）
const isInitialLoading = ref(true)


// 根据操作类型获取动作描述
const getActionVerb = (action) => {
  if (action.includes('远程')) return '尝试远程开启'
  if (action.includes('密码')) return '尝试通过密码开启'
  if (action.includes('指纹')) return '尝试通过指纹开启'
  if (action.includes('刷卡')) return '尝试通过刷卡开启'
  return '尝试开启'
}

watch(
  () => eventList.length,
  (newLen, oldLen) => {
    if (isInitialLoading.value) return  // 初始化阶段不计数
    if (newLen > oldLen) {
      stat.value.today_log += (newLen - oldLen)
    }
  }
)

// 监听设备状态变化，实时更新在线/离线数量
watch(
  deviceStatusMap,
  (map) => {
    for (const [deviceId, info] of Object.entries(map)) {
      const prev = devicePrevStatus[deviceId]
      const curr = info.status
      if (prev === curr) continue

      if (prev === undefined) {
        // 首次记录，不影响计数（初始数据来自 API）
      } else if (prev === 'offline' && curr === 'online') {
        stat.value.device_offline = Math.max(0, stat.value.device_offline - 1)
        stat.value.device_online++
      } else if (prev === 'online' && curr === 'offline') {
        stat.value.device_online = Math.max(0, stat.value.device_online - 1)
        stat.value.device_offline++
      }
      devicePrevStatus[deviceId] = curr
    }
  },
  { deep: true }
)

const now = ref(new Date())
let timer = null

const days = ['日', '一', '二', '三', '四', '五', '六']

const dateStr = computed(() => {
  const d = now.value
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 星期${days[d.getDay()]}`
})

const timeStr = computed(() => {
  const d = now.value
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
})

const roleLabel = computed(() => {
  if (role.value === 'admin') return '超级管理员'
  if (role.value === 'operator') return '普通管理员'
  return '用户'
})

const greetingText = computed(() => {
  const h = now.value.getHours()
  if (h < 6) return '夜深了，注意休息'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todaySub = computed(() => {
  const count = stat.value.today_log
  return hasPermission('log.view')
    ? `今日共有 ${count} 条开门记录`
    : `今日您有 ${count} 条开门记录`
})

const getStat = async () => {
  statLoading.value = true
  try {
    const res = await request.get('/statistics')
    if (res.success) {
      stat.value = res.data
    } else {
      ElMessage.error(res.msg || '获取统计数据失败')
    }
  } catch (e) {
    ElMessage.error('获取统计数据失败，请刷新重试')
  } finally {
    statLoading.value = false
  }
}

const goRoute = (path) => {
  router.push(path)
}

const getRecentLogs = async () => {
  logsLoading.value = true
  try {
    const res = await request.get('/door-logs', {
      params: { page: 1, size: 5 }
    })
    if (res.success) {
      recentLogs.value = res.data.list || []
    }
  } catch (e) {
    console.error('获取最近记录失败', e)
  } finally {
    logsLoading.value = false
  }
}

onMounted(() => {
  getStat()
  // 只在事件列表为空时加载历史数据，避免页面切换重复添加
  if (eventList.length === 0 && hasPermission('door.view_own_log')) {
    getRecentLogs().then(() => {
      // API 返回倒序（最新在前），reverse 后按时间正序，再 unshift 保证最新在顶部
      recentLogs.value.reverse().forEach(log => {
        addDoorEvent({
          username: log.user_id ? log.username : '本地',
          device_name: log.device_name || '未知设备',
          location: log.device_location || '',
          action: log.action || '开门',
          status: log.status || '成功',
          timestamp: log.time
        })
      })
    }).finally(() => {
      isInitialLoading.value = false  // 初始化完成，之后 WebSocket 事件才计入统计
    })
  }
  timer = setInterval(() => {
    now.value = new Date()
  }, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<style scoped>
.dashboard {
  padding: 4px;
}

.welcome-banner {
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}
.welcome-banner :deep(.el-card__body) {
  padding: 24px 28px;
}
.welcome-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}
.welcome-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.greeting-line {
  display: flex;
  align-items: center;
  gap: 6px;
}
.greeting-text {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}
.greeting-role {
  font-size: 13px;
  color: #909399;
  background: #f0f2f5;
  padding: 2px 10px;
  border-radius: 4px;
}
.welcome-sub {
  margin: 0;
  font-size: 14px;
  color: #909399;
}
.welcome-right {
  text-align: right;
}
.date-text {
  font-size: 14px;
  color: #606266;
}
.time-text {
  font-size: 32px;
  font-weight: 300;
  letter-spacing: 2px;
  color: #303133;
  font-variant-numeric: tabular-nums;
}

.stat-row {
  margin-bottom: 0;
}

.section-card {
  margin-top: 20px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.action-btn {
  height: 40px;
  padding: 0 20px;
  font-size: 14px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ai-fab-wrap {
  position: fixed;
  right: 30px;
  bottom: 30px;
  z-index: 9999;
  cursor: pointer;
}
.ai-fab {
  width: 48px;
  height: 48px;
  border: 1px solid #dcdfe6;
  border-radius: 50%;
  background: #fff;
  color: #409eff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
}
.ai-fab:hover {
  border-color: #409eff;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.2);
}

.section-card :deep(.el-table__empty-text) {
  color: #c0c4cc;
  font-size: 14px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.event-stream {
}

.event-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f2f5;
}

.event-item:last-child {
  border-bottom: none;
}

.event-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  background: #409eff;
}

.event-body {
  flex: 1;
  min-width: 0;
}

.event-main {
  font-size: 14px;
  color: #303133;
}

.event-user {
  font-weight: 600;
}

.event-sep {
  color: #909399;
  margin: 0 4px;
}

.event-device {
  font-weight: 500;
}

.event-location {
  color: #909399;
}

.event-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.event-time {
  font-size: 12px;
  color: #909399;
  font-variant-numeric: tabular-nums;
}

.event-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: #c0c4cc;
  font-size: 14px;
}

.event-empty-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
  padding: 40px 0;
}

.event-slide-enter-active {
  transition: all 0.4s ease-out;
}

.event-slide-leave-active {
  transition: all 0.3s ease-in;
}

.event-slide-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.event-slide-enter-to {
  opacity: 1;
  transform: translateY(0);
}

.event-slide-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

@media (max-width: 600px) {
  .welcome-banner :deep(.el-card__body) {
    padding: 16px;
  }
  .greeting-text {
    font-size: 17px;
  }
  .time-text {
    font-size: 22px;
    letter-spacing: 1px;
  }
  .ai-fab-wrap {
    right: 16px;
    bottom: 16px;
  }
}
</style>
