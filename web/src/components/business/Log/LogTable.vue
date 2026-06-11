<template>
  <BaseTable
    :data="logList" :loading="loading" :page="page" :size="size" :total="total"
    :page-sizes="pageSizes"
    :empty-text="emptyText"
    @update:page="emit('update:page', $event)"
    @update:size="emit('update:size', $event)"
  >
    <el-table-column v-if="showId" label="ID" prop="id" width="65" align="center" />
    <el-table-column label="时间" min-width="170">
      <template #default="{ row }">
        <el-tooltip :content="row.time" placement="top" :show-after="300">
          <span class="time-text">{{ relativeTime(row.time) }}</span>
        </el-tooltip>
      </template>
    </el-table-column>
    <el-table-column v-if="showUser" label="用户" width="160">
      <template #default="{ row }">
        <div class="user-cell">
          <span class="user-avatar" :style="{ background: avatarColor }">{{ (row.username || '?').charAt(0) }}</span>
          <div class="user-info">
            <span class="user-name">{{ row.username || '未知' }}</span>
            <span class="user-id">ID: {{ row.user_id }}</span>
          </div>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="设备" min-width="120">
      <template #default="{ row }">
        <span>{{ row.device_name }}</span>
      </template>
    </el-table-column>
    <el-table-column label="位置" prop="device_location" min-width="110" show-overflow-tooltip />
    <el-table-column v-if="showIp" label="IP地址" min-width="130">
      <template #default="{ row }">
        <span :class="{ 'ip-local': !row.ip }">{{ row.ip || '本地' }}</span>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="90" align="center">
      <template #default="{ row }">
        <el-tag :type="getActionTagType(row.action)" size="small" effect="plain">
          {{ row.action }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="状态" min-width="110" align="center">
      <template #default="{ row }">
        <el-tooltip :content="row.status" placement="top" :show-after="300">
          <el-tag :type="row.status === '成功' ? 'success' : 'danger'" size="small" effect="light">
            <span class="status-dot" :class="row.status === '成功' ? 'success' : 'fail'"></span>
            {{ getShortStatus(row.status) }}
          </el-tag>
        </el-tooltip>
      </template>
    </el-table-column>
  </BaseTable>
</template>

<script setup>
import BaseTable from '@/components/common/BaseTable.vue'
import { useRelativeTime } from '@/utils/formatTime'
import { getActionTagType, getShortStatus } from '@/utils/format'

const relativeTime = (ts) => useRelativeTime(ts)

defineProps({
  logList: Array,
  total: Number,
  page: Number,
  size: Number,
  loading: Boolean,
  showUser: { type: Boolean, default: true },
  showId: { type: Boolean, default: false },
  showIp: { type: Boolean, default: false },
  avatarColor: { type: String, default: '#6366f1' },
  emptyText: { type: String, default: '暂无日志记录' },
  pageSizes: { type: Array, default: () => [10, 20, 50] },
})
const emit = defineEmits(['update:page', 'update:size'])
</script>

<style scoped>
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.user-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.user-name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  line-height: 1.3;
}
.user-id {
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.3;
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
.status-dot.success {
  background: #22c55e;
}
.status-dot.fail {
  background: #ef4444;
}
.ip-local {
  color: #909399;
  font-size: 12px;
}
</style>
