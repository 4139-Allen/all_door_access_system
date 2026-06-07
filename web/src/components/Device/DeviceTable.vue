<template>
  <BaseTable
    :data="deviceList" :loading="loading" :page="page" :size="size" :total="total"
    empty-text="暂无设备数据"
    @update:page="emit('update:page', $event)"
    @update:size="emit('update:size', $event)"
  >
    <el-table-column label="ID" prop="id" width="70" align="center" />
    <el-table-column label="设备编号" prop="name" min-width="140">
      <template #default="{ row }">
        <span>{{ row.name }}</span>
      </template>
    </el-table-column>
    <el-table-column label="位置" prop="location" min-width="160">
      <template #default="{ row }">
        <span class="location-text">{{ row.location }}</span>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="100" align="center">
      <template #default="{ row }">
        <el-tag
          :type="row.status === 'online' ? 'success' : 'info'"
          size="small"
          effect="light"
        >
          <span class="status-dot" :class="row.status"></span>
          {{ row.status === 'online' ? '在线' : '离线' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="信号" width="90" align="center">
      <template #default="{ row }">
        <span v-if="row.status === 'online' && row.signal_strength != null" :class="['signal', signalLevel(row.signal_strength)]">
          <span class="signal-bar"></span>
          <span class="signal-bar"></span>
          <span class="signal-bar"></span>
          <span class="signal-bar"></span>
        </span>
        <span v-else class="signal signal-none">
          <span class="signal-bar"></span>
          <span class="signal-bar"></span>
          <span class="signal-bar"></span>
          <span class="signal-bar"></span>
        </span>
      </template>
    </el-table-column>
    <el-table-column label="最后在线" width="175">
      <template #default="{ row }">
        <template v-if="row.last_online_at">
          <el-tooltip :content="row.last_online_at" placement="top" :show-after="300">
            <span>{{ getRelativeTime(row.last_online_at) }}</span>
          </el-tooltip>
        </template>
        <span v-else class="time-empty">从未上线</span>
      </template>
    </el-table-column>
    <el-table-column v-if="hasPermission('device.edit') || hasPermission('device.delete')" label="操作" width="120" align="center">
      <template #default="scope">
        <el-tooltip v-if="hasPermission('device.edit')" content="编辑" placement="top" :show-after="300">
          <el-button size="small" class="action-icon-btn" @click="$emit('edit', scope.row)">
            <el-icon><Edit /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip v-if="hasPermission('device.delete')" content="删除" placement="top" :show-after="300">
          <el-button size="small" class="action-icon-btn action-icon-danger" @click="$emit('delete', scope.row.id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </el-tooltip>
      </template>
    </el-table-column>
  </BaseTable>
</template>

<script setup>
import BaseTable from '@/components/common/BaseTable.vue'
import { Edit, Delete } from '@element-plus/icons-vue'
import { useRelativeTime } from '@/utils/formatTime'
import { hasPermission } from '@/utils/permission'

const getRelativeTime = (ts) => useRelativeTime(ts)

defineProps({
  deviceList: Array,
  total: Number,
  page: Number,
  size: Number,
  loading: Boolean,
  role: { type: String, default: 'admin' },
})
const emit = defineEmits(['update:page', 'update:size', 'edit', 'delete'])

const signalLevel = (rssi) => {
  if (rssi >= -50) return 'signal-strong'
  if (rssi >= -65) return 'signal-good'
  if (rssi >= -75) return 'signal-weak'
  return 'signal-bad'
}
</script>

<style scoped>
/* Status dot indicator */
.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
}
.status-dot.online { background: #22c55e; }
.status-dot.offline { background: #94a3b8; }

.location-text {
  font-size: 13px;
  color: #64748b;
}
.action-icon-btn {
  border: 1px solid #e2e8f0;
  color: #475569;
  background: #fff;
  border-radius: 8px;
  padding: 6px;
  transition: all 0.2s;
}
.action-icon-btn:hover {
  border-color: #14b8a6;
  color: #14b8a6;
  background: #f0fdfa;
  transform: translateY(-1px);
}
.action-icon-danger:hover {
  border-color: #f56c6c;
  color: #f56c6c;
  background: #fef0f0;
}

.time-empty {
  color: #c0c4cc;
  font-size: 12px;
}

/* 信号强度 */
.signal {
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 16px;
}
.signal-bar {
  display: inline-block;
  width: 4px;
  border-radius: 1px;
  background: #dcdfe6;
}
.signal-bar:nth-child(1) { height: 4px; }
.signal-bar:nth-child(2) { height: 7px; }
.signal-bar:nth-child(3) { height: 10px; }
.signal-bar:nth-child(4) { height: 14px; }

.signal-strong .signal-bar { background: #67c23a; }
.signal-good .signal-bar:nth-child(-n+3) { background: #67c23a; }
.signal-good .signal-bar:nth-child(4) { background: #dcdfe6; }
.signal-weak .signal-bar:nth-child(-n+2) { background: #e6a23c; }
.signal-weak .signal-bar:nth-child(3),
.signal-weak .signal-bar:nth-child(4) { background: #dcdfe6; }
.signal-bad .signal-bar:nth-child(1) { background: #f56c6c; }
.signal-bad .signal-bar:nth-child(2),
.signal-bad .signal-bar:nth-child(3),
.signal-bad .signal-bar:nth-child(4) { background: #dcdfe6; }
.signal-none .signal-bar { background: #dcdfe6; }
</style>
