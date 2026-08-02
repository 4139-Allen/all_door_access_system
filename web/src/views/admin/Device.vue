<template>
  <div class="device-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <div>
          <h2 class="header-title">设备管理</h2>
          <p class="header-desc">管理门禁设备与监控设备运行状态</p>
        </div>
      </div>
      <div class="header-right">
        <span class="total-count">共 {{ total }} 台设备</span>
      </div>
    </div>

    <!-- 工具栏：搜索 + 新增设备（分两行） -->
    <div class="toolbar-card">
      <div class="toolbar-section">
        <SearchFilter
          :filter-form="filterForm"
          field="name"
          placeholder="设备编号"
          @search="resetPageAndSearch"
        />
      </div>

      <div v-if="hasPermission('device.create')" class="toolbar-section">
        <AddForm :loading="adding" @add="addDevice">
          <el-input
            v-model="addForm.name"
            placeholder="设备编号"
            style="width: 150px"
            clearable
          />
          <el-input
            v-model="addForm.location"
            placeholder="设备位置"
            style="width: 170px"
            clearable
          />
        </AddForm>
      </div>
    </div>

    <!-- 设备列表 -->
    <div class="table-card">
      <div class="table-header">
        <span class="table-header-title">设备列表</span>
        <el-tag size="small" type="info" effect="plain">
          共 {{ total }} 条记录
        </el-tag>
      </div>

      <DeviceTable
        :device-list="liveDeviceList"
        :total="total"
        :loading="loading"
        :role="role"
        v-model:page="page"
        v-model:size="size"
        @edit="editDevice"
        @delete="delDevice"
      />
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑设备" width="min(450px, 90vw)" top="30vh" @close="() => editFormRef.value?.clearValidate()">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="80px">
        <el-form-item label="设备编号" prop="name">
          <el-input v-model="editForm.name" placeholder="输入设备编号" />
        </el-form-item>
        <el-form-item label="设备位置" prop="location">
          <el-input v-model="editForm.location" placeholder="输入设备位置" />
        </el-form-item>
        <el-form-item label="设备状态">
          <el-switch
            v-model="editForm.status"
            active-value="online"
            inactive-value="offline"
            active-text="在线"
            inactive-text="离线"
            style="--el-switch-on-color: #22c55e"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useListFetch } from '@/composables/useListFetch'
import { useDeviceStatus } from '@/composables/useDeviceStatus'
import request from '@/utils/request'
import { hasPermission } from '@/utils/permission'
import { ElMessage, ElMessageBox } from 'element-plus'
import SearchFilter from '@/components/common/SearchFilter.vue'
import AddForm from '@/components/common/AddForm.vue'
import DeviceTable from '@/components/Device/DeviceTable.vue'

const role = localStorage.getItem('role') || 'user'
const { deviceStatusMap } = useDeviceStatus()

const {
  dataList: deviceList, page, size, total, loading, filterForm,
  fetchData: getDeviceList, resetPageAndSearch
} = useListFetch('/devices', {
  defaultFilter: { name: '' },
  paramsBuilder: (f) => f.name?.trim() ? { name: f.name.trim() } : {}
})

const liveDeviceList = computed(() => {
  return deviceList.value.map(d => ({
    ...d,
    status: deviceStatusMap[d.id]?.status || d.status
  }))
})

const addForm = ref({ name: '', location: '' })
const adding = ref(false)

const editDialogVisible = ref(false)
const editLoading = ref(false)
const editForm = ref({ id: null, name: '', location: '', status: 'offline' })
const editFormRef = ref(null)
const editRules = {
  name: [{ required: true, message: '请输入设备编号', trigger: 'blur' }],
  location: [{ required: true, message: '请输入设备位置', trigger: 'blur' }]
}

const addDevice = async () => {
  if (!addForm.value.name || !addForm.value.location) {
    ElMessage.warning('请输入设备编号和位置')
    return
  }
  adding.value = true
  try {
    const res = await request.post('/devices', addForm.value)
    if (res.success) {
      ElMessage.success('新增成功')
      getDeviceList()
      addForm.value = { name: '', location: '' }
    } else {
      ElMessage.error(res.msg || '新增失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || '新增失败')
  } finally {
    adding.value = false
  }
}

const editDevice = (row) => {
  editForm.value = {
    id: row.id,
    name: row.name,
    location: row.location,
    status: row.status || 'offline'
  }
  editDialogVisible.value = true
  nextTick(() => editFormRef.value?.clearValidate())
}

const saveEdit = async () => {
  if (!editFormRef.value) return
  const valid = await editFormRef.value.validate().catch(() => false)
  if (!valid) return
  editLoading.value = true
  try {
    const res = await request.put(`/devices/${editForm.value.id}`, {
      name: editForm.value.name,
      location: editForm.value.location,
      status: editForm.value.status
    })
    if (res.success) {
      ElMessage.success('更新成功')
      editDialogVisible.value = false
      getDeviceList()
    } else {
      ElMessage.error(res.msg || '更新失败')
    }
  } catch (e) {
    ElMessage.error('更新失败')
  } finally {
    editLoading.value = false
  }
}

const delDevice = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除该设备吗？请先确保已解绑所有用户。', '确认删除', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
    const res = await request.delete(`/devices/${id}`)
    if (res.success) {
      ElMessage.success('删除成功')
      getDeviceList()
    } else {
      ElMessage.error(res.msg || '删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('网络错误，请稍后重试')
    }
  }
}
</script>

<style>
@import '@/styles/page.css';
</style>

<style scoped>
.device-page {
  padding: 4px;
}

/* 搜索与新增设备各占一行 */
.toolbar-card :deep(.toolbar-section) {
  min-width: 0;
  flex: 1 0 100%;
}

.toolbar-card :deep(.toolbar-section + .toolbar-section) {
  border-top: 1px solid #ebeef5;
}
</style>
