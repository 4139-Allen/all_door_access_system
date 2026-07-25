<template>
  <BaseTable
    :data="userList" :loading="loading" :page="page" :size="size" :total="total"
    empty-text="暂无用户数据"
    @update:page="emit('update:page', $event)"
    @update:size="emit('update:size', $event)"
  >
    <el-table-column label="ID" prop="id" width="70" align="center" />
    <el-table-column label="用户名" prop="username" min-width="140">
      <template #default="{ row }">
        <div class="username-cell">
          <img v-if="row.avatar" :src="resolveAvatar(row.avatar)" class="avatar-img" />
          <span v-else class="avatar-placeholder">{{ row.username?.charAt(0)?.toUpperCase() }}</span>
          <span>{{ row.username }}</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="角色" width="130" align="center">
      <template #default="{ row }">
        <el-popover
          v-if="hasPermission('user.manage') && row.role !== 'admin' && row.username !== currentUsername"
          :visible="editingRoleId === row.id"
          placement="bottom"
          :width="160"
          trigger="click"
        >
          <template #reference>
            <el-tag
              :type="row.role === 'admin' ? 'danger' : row.role === 'operator' ? 'warning' : 'primary'"
              size="small"
              effect="light"
              class="role-tag-editable"
              @click="startEditRole(row)"
            >
              {{ row.role_name || row.role }}
              <el-icon class="role-edit-icon"><Edit /></el-icon>
            </el-tag>
          </template>
          <div class="role-popover">
            <el-select
              v-model="editingRoleValue"
              size="small"
              style="width: 100%"
              @change="(val) => confirmChangeRole(row, val)"
            >
              <el-option
                v-for="r in roleOptions"
                :key="r.code"
                :label="r.name"
                :value="r.code"
                :disabled="r.code === 'admin'"
              />
            </el-select>
            <div class="role-popover-actions">
              <el-button size="small" text @click="cancelEditRole">取消</el-button>
            </div>
          </div>
        </el-popover>
        <el-tag
          v-else
          :type="row.role === 'admin' ? 'danger' : row.role === 'operator' ? 'warning' : 'primary'"
          size="small"
          effect="light"
        >
          {{ row.role_name || row.role }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="绑定设备" min-width="180">
      <template #default="{ row }">
        <div v-if="row.devices?.length" class="device-tag-list">
          <el-tag
            v-for="name in row.devices.slice(0, 3)"
            :key="name"
            size="small"
            type="info"
            effect="plain"
          >
            {{ name }}
          </el-tag>
          <el-tag v-if="row.devices.length > 3" size="small" type="info" effect="dark">
            +{{ row.devices.length - 3 }}
          </el-tag>
        </div>
        <span v-else class="no-device">未绑定</span>
      </template>
    </el-table-column>
    <el-table-column label="创建时间" prop="created_at" width="175" />
    <el-table-column label="操作" width="120" align="center">
      <template #default="scope">
        <el-tooltip v-if="hasPermission('user.manage') && !scope.row.is_builtin && scope.row.username !== currentUsername" content="删除用户" placement="top" :show-after="300">
          <el-button size="small" class="action-icon-btn action-icon-danger" @click="$emit('delete', scope.row.id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </el-tooltip>
      </template>
    </el-table-column>
  </BaseTable>
</template>

<script setup>
import { ref, computed } from 'vue'
import BaseTable from '@/components/common/BaseTable.vue'
import { Delete, Edit } from '@element-plus/icons-vue'
import { hasPermission } from '@/utils/permission'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const resolveAvatar = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return API_BASE + path
}

const currentUsername = computed(() => localStorage.getItem('username') || '')

const props = defineProps({
  userList: Array,
  total: Number,
  page: Number,
  size: Number,
  loading: Boolean,
  roleOptions: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:page', 'update:size', 'show-devices', 'delete', 'change-role'])

// 角色编辑
const editingRoleId = ref(null)
const editingRoleValue = ref('')

const startEditRole = (row) => {
  editingRoleId.value = row.id
  editingRoleValue.value = row.role
}

const cancelEditRole = () => {
  editingRoleId.value = null
  editingRoleValue.value = ''
}

const confirmChangeRole = (row, newRole) => {
  if (newRole === row.role) {
    cancelEditRole()
    return
  }
  emit('change-role', { userId: row.id, newRole })
  cancelEditRole()
}
</script>

<style>
@import '@/styles/page.css';
</style>

<style scoped>
.username-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.avatar-img {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}
.avatar-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: #6366f1;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
  flex-shrink: 0;
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
  border-color: #6366f1;
  color: #6366f1;
  background: #f5f3ff;
  transform: translateY(-1px);
}
.action-icon-danger:hover {
  border-color: #f56c6c;
  color: #f56c6c;
  background: #fef0f0;
}

.device-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.no-device {
  color: #c0c4cc;
  font-size: 12px;
}

.role-tag-editable {
  cursor: pointer;
  position: relative;
}
.role-tag-editable:hover {
  opacity: 0.8;
}
.role-edit-icon {
  margin-left: 2px;
  font-size: 11px;
  opacity: 0.6;
}
.role-popover {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.role-popover-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
