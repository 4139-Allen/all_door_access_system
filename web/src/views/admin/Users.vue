<template>
  <div class="user-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <div>
          <h2 class="header-title">用户管理</h2>
          <p class="header-desc">管理系统用户账户与设备绑定关系</p>
        </div>
      </div>
      <div class="header-right">
        <span class="total-count">共 {{ total }} 位用户</span>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar-card">
      <div class="toolbar-section">
        <div class="section-label">搜索</div>
        <SearchFilter
          :filter-form="filterForm"
          field="username"
          placeholder="用户名"
          @search="resetPageAndSearch"
          @reset="resetFilter"
        />
      </div>

      <div v-if="hasPermission('user.manage')" class="toolbar-divider"></div>

      <div v-if="hasPermission('user.manage')" class="toolbar-section">
        <div class="section-label">新增用户</div>
        <AddForm :loading="adding" @add="addUser">
          <el-input
            v-model="addForm.username"
            placeholder="用户名（1-30位）"
            maxlength="30"
            style="width: 160px"
            clearable
          />
          <el-input
            v-model="addForm.password"
            type="password"
            placeholder="6-20位密码"
            maxlength="20"
            style="width: 170px"
            show-password
          />
          <el-select v-model="addForm.role" style="width: 120px">
            <el-option
              v-for="r in roleList"
              :key="r.code"
              :label="r.name"
              :value="r.code"
            />
          </el-select>
        </AddForm>
      </div>

      <div v-if="hasPermission('user.manage')" class="toolbar-divider"></div>

      <div v-if="hasPermission('user.manage')" class="toolbar-section">
        <div class="batch-actions">
          <el-dropdown @click="handleImportClick" @command="handleImportCommand" :loading="importing" split-button type="success" plain>
            {{ importing ? '正在导入...' : '导入 Excel' }}
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="template">下载模板</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button v-if="hasPermission('device.bind')" @click="openBindDialog">绑定/解绑设备</el-button>
          <input ref="importInput" type="file" accept=".xlsx,.xls" style="display:none" @change="handleFileChange" />
        </div>
      </div>
    </div>

    <!-- 用户列表 -->
    <div class="table-card">
      <div class="table-header">
        <span class="table-header-title">用户列表</span>
        <el-tag size="small" type="info" effect="plain">
          共 {{ total }} 条记录
        </el-tag>
      </div>

      <UserTable
        :user-list="userList"
        :total="total"
        :loading="loading"
        v-model:page="page"
        v-model:size="size"
        :role-options="roleList"
        @delete="deleteUser"
        @change-role="handleChangeRole"
      />
    </div>

    <!-- 绑定/解绑设备弹窗 -->
    <el-dialog v-model="bindDialogVisible" title="绑定/解绑设备" width="420px" top="25vh">
      <el-form label-width="80px" class="bind-form">
        <el-form-item label="选择用户">
          <el-select
            v-model="bindForm.user_id"
            placeholder="请选择用户"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="u in allUsers"
              :key="u.id"
              :label="`${u.username} (ID: ${u.id})`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="选择设备">
          <el-select
            v-model="bindForm.device_id"
            placeholder="请选择设备"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="d in allDevices"
              :key="d.id"
              :label="`${d.name} - ${d.location || '无位置'} (ID: ${d.id})`"
              :value="d.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindDialogVisible = false">取消</el-button>
        <el-button type="danger" plain :loading="unbinding" @click="unbindDevice">解绑</el-button>
        <el-button type="primary" :loading="binding" @click="bindDevice">绑定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import { useListFetch } from '@/composables/useListFetch'
import request from '@/utils/request'
import { refreshPermissions } from '@/utils/refreshPermissions'
import { hasPermission } from '@/utils/permission'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import SearchFilter from '@/components/common/SearchFilter.vue'
import AddForm from '@/components/common/AddForm.vue'
import UserTable from '@/components/User/UserTable.vue'

const {
  dataList: userList, page, size, total, loading, filterForm,
  fetchData: getUserList, resetPageAndSearch, resetFilter
} = useListFetch('/users', {
  defaultFilter: { username: '' },
  paramsBuilder: (f) => f.username?.trim() ? { username: f.username.trim() } : {}
})

const roleList = ref([])
const addForm = ref({ username: '', password: '', role: 'user' })
const bindForm = ref({ user_id: '', device_id: '' })
const adding = ref(false)
const binding = ref(false)
const unbinding = ref(false)
const importing = ref(false)
const bindDialogVisible = ref(false)
const allUsers = ref([])
const allDevices = ref([])

// 加载角色列表（用于新增用户下拉）
const loadRoles = async () => {
  try {
    const res = await request.get('/roles')
    if (res.success) roleList.value = res.data || []
  } catch (e) {}
}

// 加载所有用户和设备（用于下拉选择）
const loadAllUsers = async () => {
  try {
    const res = await request.get('/users', { params: { page: 1, size: 9999 } })
    if (res.success) allUsers.value = res.data.list || []
  } catch (e) {}
}

const loadAllDevices = async () => {
  try {
    const res = await request.get('/devices', { params: { page: 1, size: 9999 } })
    if (res.success) allDevices.value = res.data.list || []
  } catch (e) {}
}

const openBindDialog = async () => {
  bindForm.value = { user_id: '', device_id: '' }
  bindDialogVisible.value = true
  await Promise.all([loadAllUsers(), loadAllDevices()])
}

// 下载导入模板
const downloadTemplate = () => {
  const ws = XLSX.utils.aoa_to_sheet([
    ['用户名', '密码（不填默认123456）'],
    ['zhangsan', ''],
    ['lisi', 'mypassword123'],
  ])
  ws['!cols'] = [{ wch: 15 }, { wch: 25 }]
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '用户导入模板')
  XLSX.writeFile(wb, '用户导入模板.xlsx')
}

const handleImportClick = () => {
  importInput.value?.click()
}

const handleImportCommand = (command) => {
  if (command === 'template') downloadTemplate()
}

// 导入 Excel
const importInput = ref(null)

const handleFileChange = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)
  importing.value = true
  const loadingInstance = ElLoading.service({
    lock: true,
    text: '正在导入用户，请勿关闭页面...',
    background: 'rgba(0, 0, 0, 0.7)',
  })
  try {
    const res = await request.post('/users/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000
    })
    if (res.success) {
      const { success_count, fail_count, fail_list } = res.data
      if (fail_count > 0) {
        ElMessageBox.alert(
          fail_list.join('\n'),
          `导入结果：成功 ${success_count} 个，失败 ${fail_count} 个`,
          { type: 'warning', confirmButtonText: '知道了' }
        )
      } else {
        ElMessage.success(`成功导入 ${success_count} 个用户`)
      }
      getUserList()
    } else {
      ElMessage.error(res.msg || '导入失败')
    }
  } catch (err) {
    ElMessage.error('网络错误，请稍后重试')
  } finally {
    loadingInstance.close()
    importing.value = false
    e.target.value = ''
  }
}

const addUser = async () => {
  if (!addForm.value.username || !addForm.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (!/^[a-zA-Z0-9_.\-一-龥]+$/.test(addForm.value.username)) {
    ElMessage.warning('用户名只能包含字母、数字、下划线、点和中划线')
    return
  }
  adding.value = true
  try {
    const res = await request.post('/users', addForm.value)
    if (res.success) {
      ElMessage.success('新增成功')
      getUserList()
      addForm.value = { username: '', password: '', role: 'user' }
    } else {
      ElMessage.error(res.msg || '新增失败')
    }
  } catch (e) {
    ElMessage.error('网络错误，请稍后重试')
  } finally {
    adding.value = false
  }
}

const deleteUser = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该用户吗？此操作不可撤销。', '确认删除', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
    const res = await request.delete(`/users/${id}`)
    if (res.success) {
      ElMessage.success('删除成功')
      getUserList()
    } else {
      ElMessage.error(res.msg || '删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('网络错误，请稍后重试')
    }
  }
}

const handleChangeRole = async ({ userId, newRole }) => {
  const roleLabel = roleList.value.find(r => r.code === newRole)?.name || newRole
  try {
    await ElMessageBox.confirm(`确定将该用户角色修改为「${roleLabel}」吗？`, '修改角色', {
      type: 'warning',
      confirmButtonText: '确定修改',
      cancelButtonText: '取消',
    })
    const res = await request.put(`/users/${userId}/role`, { role: newRole })
    if (res.success) {
      ElMessage.success('角色修改成功')
      getUserList()
      refreshPermissions()
    } else {
      ElMessage.error(res.msg || '修改失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('网络错误，请稍后重试')
    }
  }
}

const bindDevice = async () => {
  if (!bindForm.value.user_id || !bindForm.value.device_id) {
    ElMessage.warning('请选择用户和设备')
    return
  }
  binding.value = true
  try {
    const res = await request.post(`/devices/${bindForm.value.device_id}/bind`, {
      user_id: bindForm.value.user_id
    })
    if (res.success) {
      ElMessage.success('绑定成功')
      bindForm.value = { user_id: '', device_id: '' }
    } else {
      ElMessage.error(res.msg || '绑定失败')
    }
  } catch (e) {
    ElMessage.error('网络错误，请稍后重试')
  } finally {
    binding.value = false
  }
}

const unbindDevice = async () => {
  if (!bindForm.value.user_id || !bindForm.value.device_id) {
    ElMessage.warning('请选择用户和设备')
    return
  }
  unbinding.value = true
  try {
    await ElMessageBox.confirm('确定要解绑设备吗？', '确认解绑', {
      type: 'warning',
      confirmButtonText: '确定解绑',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
    const res = await request.delete(`/devices/${bindForm.value.device_id}/unbind`, {
      params: { user_id: bindForm.value.user_id }
    })
    if (res.success) {
      ElMessage.success('解绑成功')
      bindForm.value = { user_id: '', device_id: '' }
    } else {
      ElMessage.error(res.msg || '解绑失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('网络错误，请稍后重试')
    }
  } finally {
    unbinding.value = false
  }
}

onMounted(() => {
  if (hasPermission('user.manage')) loadRoles()
})
</script>

<style>
@import '@/styles/page.css';
</style>

<style scoped>
.user-page {
  padding: 4px;
}

.toolbar-card :deep(.toolbar-section) {
  min-width: 0;
}

.batch-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.bind-form {
  padding: 0 10px;
}

.bind-form :deep(.el-select) {
  width: 100%;
}

</style>
