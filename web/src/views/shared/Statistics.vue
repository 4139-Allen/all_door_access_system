<template>
  <div class="statistics-page">
    <div class="page-header">
      <div class="header-left">
        <div>
          <h2 class="header-title">数据统计</h2>
          <p class="header-desc">查看门禁系统开锁数据与趋势分析</p>
        </div>
      </div>
    </div>

    <el-row :gutter="20" class="chart-row">
      <el-col :xs="24" :sm="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="chart-header">
              <span class="chart-title">近 7 天开锁趋势</span>
              <span class="chart-desc">每日开锁次数变化</span>
            </div>
          </template>
          <el-skeleton :loading="trendLoading" animated>
            <template #template>
              <div style="height: 260px; padding: 20px;">
                <el-skeleton-item variant="rect" style="width: 100%; height: 100%; border-radius: 8px;" />
              </div>
            </template>
            <template #default>
              <WeeklyTrend :data="trendData" />
            </template>
          </el-skeleton>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="chart-header">
              <span class="chart-title">开锁方式占比</span>
              <span class="chart-desc">各验证方式使用比例</span>
            </div>
          </template>
          <el-skeleton :loading="actionLoading" animated>
            <template #template>
              <div style="height: 260px; padding: 20px;">
                <el-skeleton-item variant="rect" style="width: 100%; height: 100%; border-radius: 8px;" />
              </div>
            </template>
            <template #default>
              <ActionPie :data="actionData" />
            </template>
          </el-skeleton>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/utils/request'
import WeeklyTrend from '@/components/Dashboard/WeeklyTrend.vue'
import ActionPie from '@/components/Dashboard/ActionPie.vue'

const trendLoading = ref(true)
const actionLoading = ref(true)
const trendData = ref([])
const actionData = ref([])

const getTrend = async () => {
  trendLoading.value = true
  try {
    const res = await request.get('/statistics/trend')
    if (res.success) trendData.value = res.data
  } catch (e) {
    console.error('获取趋势数据失败', e)
  } finally {
    trendLoading.value = false
  }
}

const getActions = async () => {
  actionLoading.value = true
  try {
    const res = await request.get('/statistics/actions')
    if (res.success) actionData.value = res.data
  } catch (e) {
    console.error('获取开锁方式数据失败', e)
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  getTrend()
  getActions()
})
</script>

<style scoped>
.statistics-page {
  padding: 4px;
}

.chart-row {
  margin-top: 20px;
}
.chart-card {
  border-radius: 8px;
  border: 1px solid #ebeef5;
  margin-bottom: 20px;
}
.chart-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.chart-desc {
  font-size: 12px;
  color: #909399;
}
</style>
