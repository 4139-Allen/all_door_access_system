<template>
  <div class="binding-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <div>
          <h2 class="header-title">绑定管理</h2>
          <p class="header-desc">查看用户绑定的设备，并完成设备绑定与解绑</p>
        </div>
      </div>
      <div class="header-right">
        <span class="total-count">共 {{ total }} 台设备</span>
      </div>
    </div>

    <!-- 用户选择 -->
    <div class="toolbar-card">
      <div class="toolbar-section">
        <div class="section-label">选择用户</div>
        <el-select
          v-model="selectedUserId"
          placeholder="搜索并选择用户"
          filterable
          clearable
          style="width: 320px"
          @change="onUserChange"
        >
          <el-option
            v-for="u in allUsers"
            :key="u.id"
            :label="`${u.username} (ID: ${u.id})`"
            :value="u.id"
          />
        </el-select>
      </div>

      <div class="toolbar-divider"></div>

      <div class="toolbar-section">
        <div class="section-label">当前用户</div>
        <div v-if="selectedUser" class="current-user">
          <span class="current-user-name">{{ selectedUser.username }}</span>
          <el-tag size="small" type="success" effect="plain">已绑定 {{ boundDevices.length }} 台设备</el-tag>
        </div>
        <span v-else class="current-user-empty">请先选择用户</span>
      </div>
    </div>

    <!-- 双栏：左=已绑定设备，右=全部设备 -->
    <div class="binding-grid">
      <div class="table-card">
        <div class="table-header">
          <span class="table-header-title">已绑定设备</span>
          <el-tag size="small" type="success" effect="plain">{{ boundDevices.length }} 台</el-tag>
        </div>
        <el-table
          :data="boundDevices"
          v-loading="boundLoading"
          height="440"
          empty-text="该用户暂无绑定设备"
        >
          <el-table-column prop="name" label="设备编号" width="130" />
          <el-table-column prop="location" label="位置" min-width="150" show-overflow-tooltip />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'online' ? 'success' : 'info'" size="small">
                {{ row.status === 'online' ? '在线' : '离线' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button
                type="danger"
                link
                size="small"
                :disabled="!selectedUserId"
                :loading="unbindingId === row.id"
                @click="unbindDevice(row)"
              >解绑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-card">
        <div class="table-header">
          <span class="table-header-title">全部设备</span>
          <div class="table-header-right">
            <el-input
              v-model="filterForm.name"
              placeholder="搜索设备编号"
              clearable
              size="default"
              style="width: 180px"
              @keyup.enter="resetPageAndSearch"
              @clear="resetPageAndSearch"
            />
            <el-button type="primary" size="default" @click="resetPageAndSearch">搜索</el-button>
          </div>
        </div>
        <el-table
          :data="deviceList"
          v-loading="loading"
          height="440"
          empty-text="暂无设备"
        >
          <el-table-column prop="name" label="设备编号" width="130" />
          <el-table-column prop="location" label="位置" min-width="150" show-overflow-tooltip />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'online' ? 'success' : 'info'" size="small">
                {{ row.status === 'online' ? '在线' : '离线' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                size="small"
                :disabled="!selectedUserId || boundDeviceIds.has(row.id)"
                :loading="bindingId === row.id"
                @click="bindDevice(row)"
              >{{ boundDeviceIds.has(row.id) ? '已绑定' : '绑定' }}</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="table-pagination">
          <el-pagination
            background
            layout="prev, pager, next"
            :total="total"
            :page-size="size"
            v-model:current-page="page"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useListFetch } from '@/composables/useListFetch'
import request from '@/utils/request'

// 全部设备（右栏，复用统一分页）
const {
  dataList: deviceList, page, size, total, loading, filterForm,
  resetPageAndSearch
} = useListFetch('/devices', {
  defaultFilter: { name: '' },
  paramsBuilder: (f) => f.name?.trim() ? { name: f.name.trim() } : {}
})

const allUsers = ref([])
const selectedUserId = ref(null)
const boundDevices = ref([])
const boundLoading = ref(false)
const bindingId = ref(null)
const unbindingId = ref(null)

const selectedUser = computed(() => allUsers.value.find(u => u.id === selectedUserId.value) || null)
const boundDeviceIds = computed(() => new Set(boundDevices.value.map(d => d.id)))

// 加载全部用户（用于选择器）
const loadUsers = async () => {
  try {
    const res = await request.get('/users', { params: { page: 1, size: 9999 } })
    if (res.success) allUsers.value = res.data.list || []
  } catch (e) {}
}

// 加载指定用户的绑定设备
const loadBoundDevices = async (userId) => {
  if (!userId) {
    boundDevices.value = []
    return
  }
  boundLoading.value = true
  try {
    const res = await request.get(`/users/${userId}/devices`)
    if (res.success) boundDevices.value = res.data || []
  } catch (e) {
    boundDevices.value = []
  } finally {
    boundLoading.value = false
  }
}

const onUserChange = (userId) => loadBoundDevices(userId)

const bindDevice = async (device) => {
  if (!selectedUserId.value) {
    ElMessage.warning('请先选择用户')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定将设备「${device.name}」绑定给用户「${selectedUser.value.username}」吗？`,
      '确认绑定',
      { type: 'warning', confirmButtonText: '确定绑定', cancelButtonText: '取消' }
    )
  } catch (e) {
    return
  }
  bindingId.value = device.id
  try {
    const res = await request.post(`/devices/${device.id}/bind`, { user_id: selectedUserId.value })
    if (res.success) {
      ElMessage.success('绑定成功')
      loadBoundDevices(selectedUserId.value)
    } else {
      ElMessage.error(res.msg || '绑定失败')
    }
  } catch (e) {
    ElMessage.error('网络错误，请稍后重试')
  } finally {
    bindingId.value = null
  }
}

const unbindDevice = async (device) => {
  if (!selectedUserId.value) {
    ElMessage.warning('请先选择用户')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定解绑用户「${selectedUser.value.username}」与设备「${device.name}」的绑定关系吗？`,
      '确认解绑',
      { type: 'warning', confirmButtonText: '确定解绑', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }
    )
  } catch (e) {
    return
  }
  unbindingId.value = device.id
  try {
    const res = await request.delete(`/devices/${device.id}/unbind`, { params: { user_id: selectedUserId.value } })
    if (res.success) {
      ElMessage.success('解绑成功')
      loadBoundDevices(selectedUserId.value)
    } else {
      ElMessage.error(res.msg || '解绑失败')
    }
  } catch (e) {
    ElMessage.error('网络错误，请稍后重试')
  } finally {
    unbindingId.value = null
  }
}

onMounted(loadUsers)
</script>

<style>
@import '@/styles/page.css';
</style>

<style scoped>
.binding-page {
  padding: 4px;
}

.current-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.current-user-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.current-user-empty {
  font-size: 14px;
  color: #c0c4cc;
}

.binding-grid {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 20px;
  align-items: start;
}

.table-header-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 14px 20px;
  border-top: 1px solid #ebeef5;
}

@media (max-width: 1100px) {
  .binding-grid {
    grid-template-columns: 1fr;
  }
}
</style>
