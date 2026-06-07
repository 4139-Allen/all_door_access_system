<template>
  <el-row :gutter="20">
    <el-col v-for="i in count" :key="i" :xs="12" :sm="6">
      <div class="skeleton-card">
        <el-skeleton :loading="true" animated>
          <template #template>
            <div class="skeleton-stat">
              <el-skeleton-item variant="button" style="width: 44px; height: 44px; border-radius: 10px;" />
              <div class="skeleton-info">
                <el-skeleton-item variant="text" style="width: 60px; height: 14px;" />
                <el-skeleton-item variant="h3" style="width: 48px; height: 28px; margin-top: 6px;" />
              </div>
            </div>
          </template>
        </el-skeleton>
      </div>
    </el-col>
  </el-row>
</template>

<script setup>
defineProps({
  count: { type: Number, default: 4 },
})
</script>

<style scoped>
.skeleton-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}
.skeleton-stat {
  display: flex;
  align-items: center;
  gap: 14px;
}
.skeleton-info {
  display: flex;
  flex-direction: column;
}
</style>
