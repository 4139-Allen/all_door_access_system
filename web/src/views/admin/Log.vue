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
        show-user
        show-labels
        @search="resetPageAndSearch"
        @reset="resetFilter"
      />
      <el-button v-if="hasPermission('log.export')" type="success" plain :loading="exporting" @click="exportExcel">
        <el-icon><Download /></el-icon>
        {{ exporting ? '正在导出...' : '导出 Excel' }}
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

const {
  dataList: logList, page, size, total, loading, filterForm,
  fetchData: getLogList, resetPageAndSearch, resetFilter
} = useListFetch('/door-logs', {
  defaultFilter: { user_id: '', device_name: '', status: '', time_range: [] },
  paramsBuilder: (f) => {
    const p = {}
    if (f.user_id?.trim()) p.user_id = f.user_id.trim()
    if (f.device_name?.trim()) p.device_name = f.device_name.trim()
    if (f.status?.trim()) p.status = f.status.trim()
    if (f.time_range?.length === 2) {
      p.start_time = f.time_range[0]
      p.end_time = f.time_range[1]
    }
    return p
  }
})

const exportExcel = async () => {
  exporting.value = true
  const msg = ElMessage.info('正在获取数据，数据量大时请耐心等待...', { duration: 0 })
  try {
    const params = {}
    const f = filterForm.value
    if (f.user_id?.trim()) params.user_id = f.user_id.trim()
    if (f.device_name?.trim()) params.device_name = f.device_name.trim()
    if (f.status?.trim()) params.status = f.status.trim()
    if (f.time_range?.length === 2) {
      params.start_time = f.time_range[0]
      params.end_time = f.time_range[1]
    }

    // 导出接口单独设 60 秒超时
    const res = await request.get('/door-logs/export', { params, timeout: 60000 })
    msg.close()

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
      ElMessage.warning('没有符合条件的记录可导出')
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
    ElMessage.success(`成功导出 ${rows.length} 条记录`)
  } catch (e) {
    msg.close()
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
</style>
