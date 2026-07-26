<template>
  <div class="door-page">
    <!-- 门禁控制 -->
    <el-card v-if="hasPermission('door.open')" class="control-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="header-title">门禁控制</span>
          </div>
          <div v-if="deviceList.length > 0" class="device-stats">
            <el-tag type="success" effect="plain" size="small">可用设备 {{ deviceList.length }} 台</el-tag>
            <el-tag type="success" effect="plain" size="small">在线 {{ onlineCount }} 台</el-tag>
            <el-tag type="info" effect="plain" size="small">离线 {{ offlineCount }} 台</el-tag>
          </div>
        </div>
      </template>
      <DoorDeviceSelect
        :device-list="deviceList"
        :loading="deviceLoading"
        v-model:selected-id="selectedDeviceId"
        :opening="doorLoading"
        :cooldown="cooldown"
        @open="openDoor"
      />
    </el-card>

    <!-- 开门记录 -->
    <el-card class="log-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="header-title">{{ hasPermission('log.view') ? '所有开门记录' : '我的开门记录' }}</span>
          </div>
          <span v-if="total > 0" class="header-total">共 {{ total }} 条</span>
        </div>
      </template>

      <LogFilter
        :filter-form="filterForm"
        @search="resetPageAndSearch"
        @reset="resetFilter"
      />

      <LogTable
        :log-list="myLogs"
        :total="total"
        :loading="logsLoading"
        :show-user="hasPermission('log.view')"
        empty-text="暂无开门记录"
        v-model:page="page"
        v-model:size="size"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useListFetch } from '@/composables/useListFetch'
import { useDeviceStatus } from '@/composables/useDeviceStatus'
import request from '@/utils/request'
import { hasPermission } from '@/utils/permission'
import { ElMessage } from 'element-plus'
import DoorDeviceSelect from '@/components/Door/DoorDeviceSelect.vue'
import LogFilter from '@/components/business/Log/LogFilter.vue'
import LogTable from '@/components/business/Log/LogTable.vue'

const { deviceStatusMap } = useDeviceStatus()

const deviceList = ref([])
const selectedDeviceId = ref(null)
const deviceLoading = ref(false)
const doorLoading = ref(false)
const role = ref(localStorage.getItem('role') || '')

const onlineCount = computed(() => deviceList.value.filter(d => (deviceStatusMap[d.id]?.status || d.status) === 'online').length)
const offlineCount = computed(() => deviceList.value.length - onlineCount.value)

const {
  dataList: myLogs, page, size, total,
  loading: logsLoading, filterForm,
  fetchData: getMyLogs, resetPageAndSearch, resetFilter
} = useListFetch('/door/my-logs', {
  immediate: false,
  defaultFilter: { device_name: '', status: '', time_range: [] },
  paramsBuilder: (f) => {
    const p = {}
    if (f.device_name?.trim()) p.device_name = f.device_name.trim()
    if (f.status?.trim()) p.status = f.status.trim()
    if (f.time_range?.length === 2) {
      p.start_time = f.time_range[0]
      p.end_time = f.time_range[1]
    }
    return p
  }
})

const getMyDevices = async () => {
  deviceLoading.value = true
  try {
    const res = await request.get('/devices')
    if (res.success) {
      deviceList.value = res.data.list || []
    }
  } catch (e) {
    console.error('获取设备失败', e)
  } finally {
    deviceLoading.value = false
  }
}

// 冷却时间控制
const cooldown = ref(0)
let cooldownTimer = null

const startCooldown = (seconds = 3) => {
  cooldown.value = seconds
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    cooldown.value--
    if (cooldown.value <= 0) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

const openDoor = async () => {
  if (!selectedDeviceId.value) {
    ElMessage.warning('请选择设备')
    return
  }
  if (cooldown.value > 0) {
    ElMessage.warning(`请等待 ${cooldown.value} 秒后再试`)
    return
  }
  doorLoading.value = true
  try {
    const res = await request.post(`/doors/${selectedDeviceId.value}/open`)
    if (res.success) {
      ElMessage.success(res.msg || '开门成功')
      startCooldown(3)
      getMyLogs()
    } else {
      ElMessage.error(res.msg || '开门失败')
    }
  } catch (e) {
    if (e?.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，设备可能未响应')
    } else if (e?.response?.status === 403) {
      ElMessage.error(e.response.data?.msg || '无权限操作该设备')
      // 如果是冷却错误，启动前端冷却计时
      if (e.response.data?.msg?.includes('频繁')) {
        startCooldown(3)
      }
    } else if (e?.response?.status === 404) {
      ElMessage.error('设备不存在')
    } else if (!e?.response) {
      ElMessage.error('网络连接失败，请检查网络')
    } else {
      ElMessage.error(e.response.data?.msg || '开门失败，请稍后重试')
    }
  } finally {
    setTimeout(() => { doorLoading.value = false }, 300)
  }
}

onMounted(() => {
  getMyDevices()
  if (hasPermission('door.view_own_log')) getMyLogs()
})
</script>

<style scoped>
.door-page {
  padding: 4px;
}

.control-card,
.log-card {
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.log-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.header-total {
  font-size: 13px;
  color: #909399;
}
.device-stats {
  display: flex;
  gap: 8px;
}
</style>
