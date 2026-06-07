<template>
  <div class="door-control">
    <div class="control-row">
      <div class="select-wrap">
        <el-select
          :model-value="selectedId"
          @update:model-value="$emit('update:selectedId', $event)"
          placeholder="请选择设备"
          size="large"
          class="device-select"
          :loading="loading"
        >
          <el-option
            v-for="d in liveDeviceList"
            :key="d.id"
            :label="`${d.name} | ${d.location}`"
            :value="d.id"
            :disabled="d.status !== 'online'"
          >
            <div class="option-item">
              <span class="option-status" :class="d.status === 'online' ? 'online' : 'offline'"></span>
              <span class="option-name">{{ d.name }}</span>
              <span class="option-location">{{ d.location }}</span>
            </div>
          </el-option>
        </el-select>
      </div>
      <el-tooltip
        :content="buttonDisabled ? (selectedId ? '设备离线，无法开门' : '请先选择设备') : ''"
        placement="top"
        :disabled="!buttonDisabled"
      >
        <el-button
          type="primary"
          size="large"
          class="open-btn"
          :class="{ 'open-btn-success': justOpened }"
          :disabled="buttonDisabled"
          :loading="opening"
          @click="handleOpen"
        >
          <el-icon :size="18">
            <Unlock v-if="justOpened" />
            <Lock v-else />
          </el-icon>
          <span>{{ opening ? '开门中...' : (justOpened ? '已开锁' : (buttonDisabled ? '不可开门' : '开锁')) }}</span>
        </el-button>
      </el-tooltip>
    </div>

    <!-- 已选设备信息 -->
    <div v-if="selectedDevice" class="device-info-card">
      <div class="device-info-left">
        <span class="device-status-dot" :class="selectedDevice.status"></span>
        <div class="device-info-text">
          <span class="device-name">{{ selectedDevice.name }}</span>
          <span class="device-location">{{ selectedDevice.location }}</span>
        </div>
      </div>
      <div class="device-status-tag">
        <el-tag
          :type="selectedDevice.status === 'online' ? 'success' : 'info'"
          effect="plain"
          size="small"
        >
          {{ selectedDevice.status === 'online' ? '在线' : '离线' }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Lock, Unlock } from '@element-plus/icons-vue'
import { useDeviceStatus } from '@/composables/useDeviceStatus'

const { deviceStatusMap } = useDeviceStatus()

const props = defineProps({
  deviceList: Array,
  selectedId: [String, Number],
  loading: Boolean,
  opening: Boolean,
})
const emit = defineEmits(['open', 'update:selectedId'])

const justOpened = ref(false)
let openTimer = null

const handleOpen = () => {
  emit('open')
  justOpened.value = true
  clearTimeout(openTimer)
  openTimer = setTimeout(() => { justOpened.value = false }, 2000)
}

const liveDeviceList = computed(() => {
  return (props.deviceList || []).map(d => ({
    ...d,
    status: deviceStatusMap[d.id]?.status || d.status
  }))
})

const selectedDevice = computed(() => {
  if (!props.selectedId || !liveDeviceList.value) return null
  return liveDeviceList.value.find(d => d.id === props.selectedId) || null
})

const buttonDisabled = computed(() => {
  return !props.selectedId || selectedDevice.value?.status !== 'online'
})
</script>

<style scoped>
.door-control {
  padding: 4px 0;
}
.control-row {
  display: flex;
  gap: 14px;
  align-items: center;
}
.select-wrap {
  flex: 1;
}
.device-select {
  width: 100%;
}
.device-select :deep(.el-input__wrapper) {
  border-radius: 10px;
  height: 44px;
  padding: 0 16px;
}
.device-select :deep(.el-input__inner) {
  font-size: 14px;
}
.open-btn {
  height: 44px;
  padding: 0 28px;
  border-radius: 10px;
  font-size: 15px;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.25s;
  flex-shrink: 0;
}
.open-btn:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.35);
}
.open-btn-success {
  background: #22c55e !important;
  border-color: #22c55e !important;
  animation: unlock-bounce 0.4s ease;
}
@keyframes unlock-bounce {
  0% { transform: scale(1); }
  30% { transform: scale(1.08); }
  60% { transform: scale(0.96); }
  100% { transform: scale(1); }
}

/* 设备信息卡片 */
.device-info-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  padding: 12px 16px;
  background: #f7f8fa;
  border: 1px solid #e8eaed;
  border-radius: 10px;
  transition: all 0.2s;
}
.device-info-card:hover {
  background: #f0f7ff;
  border-color: #a6c8ff;
}
.device-info-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.device-status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.device-status-dot.online {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.5);
}
.device-status-dot.offline {
  background: #c0c4cc;
}
.device-info-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.device-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.device-location {
  font-size: 12px;
  color: #909399;
}

/* 选项内样式 */
.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
}
.option-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.option-status.online { background: #67c23a; }
.option-status.offline { background: #c0c4cc; }
.option-name {
  font-weight: 500;
  color: #303133;
}
.option-location {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}
</style>
