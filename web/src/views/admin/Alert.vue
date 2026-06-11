<template>
  <div class="alert-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <div>
          <h2 class="header-title">异常事件</h2>
          <p class="header-desc">查看设备锁定、开门失败等安全事件</p>
        </div>
      </div>
      <div class="header-right">
        <el-tag type="danger" effect="plain" size="small">
          锁定设备 {{ lockedDevices.length }} 台
        </el-tag>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon stat-icon-total">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ alertStats.total_alerts || 0 }}</span>
          <span class="stat-label">24小时异常总数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-lock">
          <el-icon><Lock /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ alertStats.lock_count || 0 }}</span>
          <span class="stat-label">设备锁定次数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon-error">
          <el-icon><CircleClose /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ alertStats.error_count || 0 }}</span>
          <span class="stat-label">开门失败次数</span>
        </div>
      </div>
    </div>

    <!-- 锁定设备列表 -->
    <el-card v-if="lockedDevices.length > 0" class="locked-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><Lock /></el-icon>
            当前锁定设备
          </span>
        </div>
      </template>
      <div class="locked-list">
        <div v-for="device in lockedDevices" :key="device.device_id" class="locked-item">
          <div class="locked-info">
            <span class="locked-name">{{ device.device_name }}</span>
            <span class="locked-location">{{ device.device_location }}</span>
          </div>
          <div class="locked-actions">
            <span class="locked-ttl">剩余 {{ device.lock_ttl }} 秒</span>
            <el-button
              v-if="hasPermission('alert.unlock')"
              type="danger"
              size="small"
              :loading="unlockingId === device.device_name"
              @click="handleUnlock(device.device_name)"
            >
              解除锁定
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 筛选 -->
    <div class="filter-card">
      <div class="filter-row">
        <div class="filter-item">
          <span class="filter-label">设备</span>
          <el-input
            v-model="filterForm.device_name"
            placeholder="设备编号"
            style="width: 160px"
            clearable
            size="default"
          />
        </div>
        <div class="filter-item">
          <span class="filter-label">事件类型</span>
          <el-select v-model="filterForm.alert_type" style="width: 140px" clearable placeholder="全部" size="default">
            <el-option label="设备锁定" value="lock" />
            <el-option label="开门失败" value="error" />
            <el-option label="设备离线" value="offline" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">时间</span>
          <el-date-picker
            v-model="filterForm.time_range"
            type="daterange"
            value-format="YYYY-MM-DD HH:mm:ss"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 280px"
            size="default"
          />
        </div>
        <div class="filter-actions">
          <el-button type="primary" size="default" @click="resetPageAndSearch">搜索</el-button>
          <el-button size="default" @click="resetFilter">重置</el-button>
        </div>
      </div>
    </div>

    <!-- 事件列表 -->
    <div class="table-card">
      <div class="table-header">
        <span class="table-header-title">事件记录</span>
        <el-tag size="small" type="info" effect="plain">
          共 {{ total }} 条记录
        </el-tag>
      </div>

      <BaseTable
        :data="alertList"
        :loading="loading"
        :page="page"
        :size="size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        empty-text="暂无异常事件"
        @update:page="page = $event"
        @update:size="size = $event"
      >
        <el-table-column label="时间" min-width="170">
          <template #default="{ row }">
            <el-tooltip :content="row.time" placement="top" :show-after="300">
              <span class="time-text">{{ relativeTime(row.time) }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="设备" min-width="120">
          <template #default="{ row }">
            <span>{{ row.device_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="位置" prop="device_location" min-width="110" show-overflow-tooltip />
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="getActionTagType(row.action)" size="small" effect="plain">
              {{ row.action }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="事件类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getEventTypeTag(row.event_type)" size="small" effect="light">
              {{ getEventTypeName(row.event_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="130" align="center">
          <template #default="{ row }">
            <el-tooltip :content="row.status" placement="top" :show-after="300">
              <el-tag :type="row.event_level === 'danger' ? 'danger' : 'warning'" size="small" effect="light">
                <span class="status-dot" :class="row.event_level"></span>
                {{ getShortStatus(row.status) }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
      </BaseTable>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, Lock, CircleClose } from '@element-plus/icons-vue'
import { useListFetch } from '@/composables/useListFetch'
import { useRelativeTime } from '@/utils/formatTime'
import { hasPermission } from '@/utils/permission'
import { getActionTagType, getShortStatus } from '@/utils/format'
import request from '@/utils/request'
import BaseTable from '@/components/common/BaseTable.vue'

const relativeTime = (ts) => useRelativeTime(ts)

// 统计数据
const alertStats = ref({})
const lockedDevices = ref([])
const unlockingId = ref(null)

// 锁定倒计时
let countdownTimer = null
const startCountdown = () => {
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    let hasLocked = false
    lockedDevices.value.forEach(d => {
      if (d.lock_ttl > 0) {
        d.lock_ttl--
        hasLocked = true
      }
    })
    // 所有设备解锁后停止倒计时，刷新数据
    if (!hasLocked) {
      clearInterval(countdownTimer)
      countdownTimer = null
      getAlertStats()
    }
  }, 1000)
}

// 事件列表
const {
  dataList: alertList, page, size, total, loading, filterForm,
  fetchData: getAlertList, resetPageAndSearch, resetFilter
} = useListFetch('/alerts', {
  defaultFilter: { device_name: '', alert_type: '', time_range: [] },
  paramsBuilder: (f) => {
    const p = {}
    if (f.device_name?.trim()) p.device_name = f.device_name.trim()
    if (f.alert_type?.trim()) p.alert_type = f.alert_type.trim()
    if (f.time_range?.length === 2) {
      p.start_time = f.time_range[0]
      p.end_time = f.time_range[1]
    }
    return p
  }
})

// 获取统计数据
const getAlertStats = async () => {
  try {
    const res = await request.get('/alerts/stats', { params: { hours: 24 } })
    if (res.code === 200) {
      alertStats.value = res.data
      lockedDevices.value = res.data.locked_devices || []
      // 有锁定设备时启动倒计时
      if (lockedDevices.value.length > 0) {
        startCountdown()
      }
    }
  } catch (e) {
    console.error('获取统计失败', e)
  }
}

// 解除锁定
const handleUnlock = async (deviceName) => {
  try {
    await ElMessageBox.confirm(
      `确定要解除设备「${deviceName}」的锁定吗？`,
      '解除锁定',
      { type: 'warning' }
    )
    unlockingId.value = deviceName
    const res = await request.post(`/alerts/unlock/${deviceName}`)
    if (res.code === 200) {
      ElMessage.success(res.msg || '解除成功')
      getAlertStats()
      getAlertList()
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('解除失败')
    }
  } finally {
    unlockingId.value = null
  }
}

// 事件类型
const getEventTypeTag = (type) => {
  if (type === 'lock') return 'danger'
  if (type === 'offline') return 'warning'
  return 'info'
}

const getEventTypeName = (type) => {
  if (type === 'lock') return '锁定'
  if (type === 'offline') return '离线'
  return '失败'
}

onMounted(() => {
  getAlertStats()
})

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style>
@import '@/styles/page.css';
</style>

<style scoped>
.alert-page {
  padding: 4px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-icon-total {
  background: #fef3cd;
  color: #856404;
}

.stat-icon-lock {
  background: #f8d7da;
  color: #721c24;
}

.stat-icon-error {
  background: #d1ecf1;
  color: #0c5460;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.locked-card {
  margin-bottom: 16px;
  border: 1px solid #f56c6c;
}

.card-header {
  display: flex;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #f56c6c;
}

.locked-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.locked-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fef0f0;
  border-radius: 8px;
  border: 1px solid #fbc4c4;
}

.locked-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.locked-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.locked-location {
  font-size: 13px;
  color: #909399;
}

.locked-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.locked-ttl {
  font-size: 13px;
  color: #f56c6c;
  font-weight: 500;
}

.filter-card {
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  letter-spacing: 0.3px;
}

.filter-actions {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding-bottom: 1px;
}

.table-card {
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  padding: 16px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.table-header-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.time-text {
  font-size: 13px;
  color: #64748b;
  font-variant-numeric: tabular-nums;
}

.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
}

.status-dot.danger {
  background: #f56c6c;
}

.status-dot.warning {
  background: #e6a23c;
}
</style>