<template>
  <div class="role-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <div>
          <h2 class="header-title">权限管理</h2>
          <p class="header-desc">管理角色及其权限分配</p>
        </div>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>新建角色
        </el-button>
      </div>
    </div>

    <!-- 角色列表 -->
    <div v-loading="loading" class="role-grid">
      <el-card
        v-for="role in roleList"
        :key="role.id"
        shadow="never"
        class="role-card"
      >
        <div class="role-card-header">
          <div class="role-info">
            <span class="role-name">{{ role.name }}</span>
            <el-tag v-if="role.is_system" size="small" type="info" effect="plain">系统内置</el-tag>
            <el-tag v-else size="small" type="warning" effect="plain">自定义</el-tag>
          </div>
          <div class="role-actions">
            <el-button v-if="role.role_code !== 'admin'" size="small" @click="openPermDialog(role)">
              <el-icon><Setting /></el-icon>权限
            </el-button>
            <el-button
              v-if="!role.is_system"
              size="small"
              type="danger"
              plain
              @click="handleDelete(role)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>

        <div class="role-code">{{ role.role_code }}</div>

        <div class="role-perms">
          <template v-if="role.permissions.length > 0">
            <el-tag
              v-for="perm in role.permissions"
              :key="perm.id"
              size="small"
              effect="plain"
              class="perm-tag"
            >
              {{ perm.name }}
            </el-tag>
          </template>
          <span v-else class="no-perm">暂无权限</span>
        </div>
      </el-card>
    </div>

    <!-- 权限设置弹窗 -->
    <el-dialog
      v-model="permDialogVisible"
      :title="`设置权限 - ${editingRole?.name || ''}`"
      width="560px"
      top="8vh"
    >
      <div v-loading="permLoading" class="perm-dialog-body">
        <div v-for="group in allPermissions" :key="group.module" class="perm-group">
          <div class="perm-group-title">
            <span>{{ group.module }}</span>
            <el-checkbox
              :model-value="isModuleAllChecked(group)"
              :indeterminate="isModuleIndeterminate(group)"
              @change="toggleModule(group, $event)"
            >
              全选
            </el-checkbox>
          </div>
          <div class="perm-group-items">
            <el-checkbox
              v-for="p in group.permissions"
              :key="p.id"
              :model-value="checkedIds.has(p.id)"
              @change="togglePerm(p.id, $event)"
            >
              {{ p.name }}
            </el-checkbox>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="permDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePermissions">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新建角色弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建角色" width="420px" top="25vh">
      <el-form label-width="80px">
        <el-form-item label="角色名称">
          <el-input v-model="createForm.name" placeholder="如：设备运维员" maxlength="30" />
        </el-form-item>
        <el-form-item label="角色标识">
          <el-input v-model="createForm.code" placeholder="如：device_admin" maxlength="30" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Setting, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { refreshPermissions } from '@/utils/refreshPermissions'

const loading = ref(false)
const roleList = ref([])
const allPermissions = ref([])

// ======== 角色列表 ========
const fetchRoles = async () => {
  loading.value = true
  try {
    const res = await request.get('/roles')
    if (res.success) roleList.value = res.data || []
  } catch (e) {
    ElMessage.error('获取角色列表失败')
  } finally {
    loading.value = false
  }
}

// ======== 权限设置 ========
const permDialogVisible = ref(false)
const permLoading = ref(false)
const saving = ref(false)
const editingRole = ref(null)
const checkedIds = reactive(new Set())

const fetchAllPermissions = async () => {
  try {
    const res = await request.get('/permissions')
    if (res.success) allPermissions.value = res.data || []
  } catch (e) {
    ElMessage.error('获取权限列表失败')
  }
}

const openPermDialog = async (role) => {
  editingRole.value = role
  checkedIds.clear()
  role.permissions.forEach(p => checkedIds.add(p.id))
  permDialogVisible.value = true

  if (allPermissions.value.length === 0) {
    permLoading.value = true
    await fetchAllPermissions()
    permLoading.value = false
  }
}

const isModuleAllChecked = (group) => {
  return group.permissions.every(p => checkedIds.has(p.id))
}

const isModuleIndeterminate = (group) => {
  const checked = group.permissions.filter(p => checkedIds.has(p.id)).length
  return checked > 0 && checked < group.permissions.length
}

const toggleModule = (group, checked) => {
  group.permissions.forEach(p => {
    if (checked) {
      checkedIds.add(p.id)
    } else {
      checkedIds.delete(p.id)
    }
  })
}

const togglePerm = (id, checked) => {
  if (checked) {
    checkedIds.add(id)
  } else {
    checkedIds.delete(id)
  }
}

const savePermissions = async () => {
  saving.value = true
  try {
    const res = await request.put(`/roles/${editingRole.value.id}/permissions`, {
      permission_ids: [...checkedIds]
    })
    if (res.success) {
      ElMessage.success('权限设置成功')
      permDialogVisible.value = false
      fetchRoles()
      // 如果当前用户也被该角色影响，刷新权限缓存
      refreshPermissions()
    } else {
      ElMessage.error(res.msg || '设置失败')
    }
  } catch (e) {
    ElMessage.error('网络错误')
  } finally {
    saving.value = false
  }
}

// ======== 新建角色 ========
const createDialogVisible = ref(false)
const creating = ref(false)
const createForm = reactive({ name: '', code: '' })

const openCreateDialog = () => {
  createForm.name = ''
  createForm.code = ''
  createDialogVisible.value = true
}

const handleCreate = async () => {
  if (!createForm.name.trim() || !createForm.code.trim()) {
    ElMessage.warning('请填写角色名称和标识')
    return
  }
  creating.value = true
  try {
    const res = await request.post('/roles', {
      name: createForm.name.trim(),
      code: createForm.code.trim()
    })
    if (res.success) {
      ElMessage.success('创建成功')
      createDialogVisible.value = false
      fetchRoles()
    } else {
      ElMessage.error(res.msg || '创建失败')
    }
  } catch (e) {
    ElMessage.error('网络错误')
  } finally {
    creating.value = false
  }
}

// ======== 删除角色 ========
const handleDelete = async (role) => {
  try {
    await ElMessageBox.confirm(
      `确定删除角色「${role.name}」吗？`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    const res = await request.delete(`/roles/${role.id}`)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchRoles()
    } else {
      ElMessage.error(res.msg || '删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('网络错误')
  }
}

onMounted(() => {
  fetchRoles()
})
</script>

<style>
@import '@/styles/page.css';
</style>

<style scoped>
.role-page {
  padding: 4px;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.role-card {
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.role-card :deep(.el-card__body) {
  padding: 20px;
}

.role-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.role-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.role-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.role-actions {
  display: flex;
  gap: 6px;
}

.role-code {
  font-size: 12px;
  color: #909399;
  font-family: monospace;
  margin-bottom: 12px;
}

.role-perms {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.perm-tag {
  font-size: 12px;
}

.no-perm {
  font-size: 13px;
  color: #c0c4cc;
}

/* 权限弹窗 */
.perm-dialog-body {
  max-height: 60vh;
  overflow-y: auto;
  padding: 0 4px;
}

.perm-group {
  margin-bottom: 20px;
}

.perm-group:last-child {
  margin-bottom: 0;
}

.perm-group-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f2f5;
  margin-bottom: 10px;
}

.perm-group-items {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  padding-left: 4px;
}

@media (max-width: 600px) {
  .role-grid {
    grid-template-columns: 1fr;
  }
}
</style>
