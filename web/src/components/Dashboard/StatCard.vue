<template>
  <el-col :xs="12" :sm="6" :md="6" :lg="6">
    <el-card shadow="never" class="stat-card">
      <div class="stat-body">
        <div class="stat-icon-wrap" :style="{ background: color + '10', color }">
          <el-icon :size="20"><component :is="icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-title">{{ title }}</div>
          <div class="stat-number" :style="{ color }">{{ number }}</div>
        </div>
      </div>
    </el-card>
  </el-col>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  number: { type: [Number, String], default: 0 },
  color: { type: String, default: '#409eff' },
  icon: { type: [Object, String], default: null },
})
</script>

<style scoped>
.stat-card {
  margin-bottom: 20px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.stat-body {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 4px 0;
}

.stat-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  min-width: 0;
}

.stat-title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-number {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
}
</style>
