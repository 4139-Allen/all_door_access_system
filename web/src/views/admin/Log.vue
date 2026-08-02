<template>
  <div class="log-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <div>
          <h2 class="header-title">门禁日志</h2>
          <p class="header-desc">查看所有门禁开关记录与操作历史</p>
        </div>
      </div>
      <div class="header-right">
        <span class="total-count">共 {{ total }} 条记录</span>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-card">
      <LogFilter
        :filter-form="filterForm"
        :show-user="isAdmin"
        show-labels
        @search="resetPageAndSearch"
        @reset="resetFilter"
      />
      <el-button v-if="hasPermission('log.export')" type="success" plain @click="openExport">
        <el-icon><Download /></el-icon>
        导出 Excel
      </el-button>
    </div>

    <!-- 列表 -->
    <div class="table-card">
      <div class="table-header">
        <span class="table-header-title">开门记录</span>
        <el-tag size="small" type="info" effect="plain">
          共 {{ total }} 条记录
        </el-tag>
      </div>

      <LogTable
        :log-list="logList"
        :total="total"
        :loading="loading"
        show-id
        show-ip
        avatar-color="#d97706"
        :page-sizes="[10, 20, 50, 100]"
        v-model:page="page"
        v-model:size="size"
      />
    </div>

    <!-- 导出确认对话框 -->
    <el-dialog
      v-model="exportVisible"
      title="导出门禁日志"
      width="560px"
      :close-on-click-modal="false"
      :close-on-press-escape="!exporting"
    >
      <p class="export-tip">设置导出条件后点击「确认导出」，将按条件生成 Excel 文件。</p>
      <LogFilter
        :filter-form="exportFilter"
        :show-user="isAdmin"
        show-labels
        :show-actions="false"
      />
      <template #footer>
        <el-button size="default" :disabled="exporting" @click="exportVisible = false">取消</el-button>
        <el-button size="default" :disabled="exporting" @click="resetExportFilter">重置</el-button>
        <el-button type="success" :loading="exporting" @click="confirmExport">
          {{ exporting ? '正在导出...' : '确认导出' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import { useListFetch } from '@/composables/useListFetch'
import request from '@/utils/request'
import { hasPermission } from '@/utils/permission'
import LogFilter from '@/components/business/Log/LogFilter.vue'
import LogTable from '@/components/business/Log/LogTable.vue'

const exporting = ref(false)
const exportVisible = ref(false)

// 导出对话框独立筛选条件（与页面筛选分离，打开时预填当前条件）
const defaultExportFilter = { username: '', device_name: '', status: '', time_range: [] }
const exportFilter = ref({ ...defaultExportFilter })

// 根据权限选择接口：管理员查全部，普通用户只看自己的
const isAdmin = hasPermission('log.view')
const logApiUrl = isAdmin ? '/door-logs' : '/door/my-logs'

const {
  dataList: logList, page, size, total, loading, filterForm,
  fetchData: getLogList, resetPageAndSearch, resetFilter
} = useListFetch(logApiUrl, {
  defaultFilter: { username: '', device_name: '', status: '', time_range: [] },
  paramsBuilder: (f) => {
    const p = {}
    if (isAdmin && f.username?.trim()) p.username = f.username.trim()
    if (f.device_name?.trim()) p.device_name = f.device_name.trim()
    if (f.status?.trim()) p.status = f.status.trim()
    if (f.time_range?.length === 2) {
      p.start_time = f.time_range[0]
      p.end_time = f.time_range[1]
    }
    return p
  }
})

// 打开导出对话框，预填当前页面筛选条件
const openExport = () => {
  exportFilter.value = { ...filterForm.value }
  exportVisible.value = true
}

// 重置导出对话框筛选条件
const resetExportFilter = () => {
  exportFilter.value = { ...defaultExportFilter }
}

// 将导出筛选条件转为请求参数
const buildExportParams = (f) => {
  const params = {}
  if (f.username?.trim()) params.username = f.username.trim()
  if (f.device_name?.trim()) params.device_name = f.device_name.trim()
  if (f.status?.trim()) params.status = f.status.trim()
  if (f.time_range?.length === 2) {
    params.start_time = f.time_range[0]
    params.end_time = f.time_range[1]
  }
  return params
}

// 确认导出：按对话框内筛选条件导出
const confirmExport = async () => {
  try {
    exporting.value = true

    const params = buildExportParams(exportFilter.value)
    const res = await request.get('/door-logs/export', { params, timeout: 60000 })

    if (!res.success) {
      ElMessage.error(res.msg || '导出失败')
      return
    }

    const rows = (res.data.list || []).map((item, i) => ({
      '序号': i + 1,
      '时间': item.time,
      '用户': item.username,
      '设备编号': item.device_name,
      '位置': item.device_location,
      '操作': item.action,
      '状态': item.status,
      'IP地址': item.ip || '本地'
    }))

    if (rows.length === 0) {
      ElMessage.warning('没有符合条件的记录可导出，请调整筛选条件')
      return
    }

    const ws = XLSX.utils.json_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '开门记录')

    ws['!cols'] = [
      { wch: 6 }, { wch: 20 }, { wch: 10 },
      { wch: 12 }, { wch: 15 }, { wch: 8 },
      { wch: 15 }, { wch: 15 }
    ]

    const now = new Date()
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
    XLSX.writeFile(wb, `门禁日志_${dateStr}.xlsx`)
    if (res.data?.truncated) {
      const maxRows = res.data.max_rows || rows.length
      ElMessage.warning(`记录较多，已按上限导出最新 ${rows.length} 条（上限 ${maxRows} 条），如需完整数据请缩小筛选范围`)
    } else {
      ElMessage.success(`成功导出 ${rows.length} 条记录`)
    }
    exportVisible.value = false
  } catch (e) {
    if (e.code === 'ECONNABORTED' || e.message?.includes('timeout')) {
      ElMessage.error('导出超时，请缩小筛选范围后重试')
    } else {
      ElMessage.error('导出失败，请稍后重试')
    }
  } finally {
    exporting.value = false
  }
}
</script>

<style>
@import '@/styles/page.css';
</style>

<style scoped>
.log-page {
  padding: 4px;
}

.filter-card {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.export-tip {
  margin: 0 0 16px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}
</style>
