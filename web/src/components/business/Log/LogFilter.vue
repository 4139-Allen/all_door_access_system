<template>
  <div class="filter-row">
    <div v-if="showUser" class="filter-item">
      <span v-if="showLabels" class="filter-label">用户</span>
      <el-input
        v-model="filterForm.username"
        placeholder="用户名"
        style="width: 140px"
        clearable
        size="default"
      />
    </div>
    <div class="filter-item">
      <span v-if="showLabels" class="filter-label">设备</span>
      <el-input
        v-model="filterForm.device_name"
        placeholder="设备名"
        style="width: 160px"
        clearable
        size="default"
      />
    </div>
    <div class="filter-item">
      <span v-if="showLabels" class="filter-label">状态</span>
      <el-select v-model="filterForm.status" style="width: 130px" clearable placeholder="全部" size="default">
        <el-option label="成功" value="成功" />
        <el-option label="失败" value="失败" />
      </el-select>
    </div>
    <div class="filter-item">
      <span v-if="showLabels" class="filter-label">时间</span>
      <el-date-picker
        v-model="filterForm.time_range"
        type="daterange"
        value-format="YYYY-MM-DD HH:mm:ss"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        style="width: 280px"
        size="default"
      />
    </div>
    <div v-if="showActions" class="filter-actions">
      <el-button type="primary" size="default" @click="$emit('search')">搜索</el-button>
      <el-button size="default" @click="$emit('reset')">重置</el-button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  filterForm: { type: Object, required: true },
  showUser: Boolean,
  showLabels: Boolean,
  // 是否显示「搜索 / 重置」操作按钮，导出对话框等场景可隐藏
  showActions: { type: Boolean, default: true },
})
defineEmits(['search', 'reset'])
</script>

<style scoped>
.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 16px;
  width: 100%;
}
.filter-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.filter-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  letter-spacing: 0.3px;
}
.filter-actions {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding-bottom: 1px;
}
</style>
