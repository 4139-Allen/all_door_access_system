<template>
  <div class="skeleton-wrap">
    <div v-for="i in rows" :key="i" class="skeleton-row">
      <div v-for="j in cols" :key="j" class="skeleton-cell" :style="{ width: cellWidths[j - 1] || '120px' }">
        <el-skeleton :loading="true" animated>
          <template #template>
            <el-skeleton-item variant="text" style="height: 16px; width: 100%;" />
          </template>
        </el-skeleton>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  rows: { type: Number, default: 5 },
  cols: { type: Number, default: 4 },
  cellWidths: { type: Array, default: () => [] },
})
</script>

<style scoped>
.skeleton-wrap {
  padding: 16px 20px;
}
.skeleton-row {
  display: flex;
  gap: 20px;
  padding: 14px 0;
  border-bottom: 1px solid #f0f2f5;
}
.skeleton-row:last-child {
  border-bottom: none;
}
.skeleton-cell {
  flex-shrink: 0;
}
</style>
