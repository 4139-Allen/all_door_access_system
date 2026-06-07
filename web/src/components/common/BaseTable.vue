<template>
  <div class="table-wrapper">
    <el-table
      v-bind="$attrs"
      class="custom-table"
      stripe
      v-loading="loading"
    >
      <slot />
      <template #empty>
        <div v-if="loading" class="skeleton-rows">
          <div v-for="i in 5" :key="i" class="skeleton-row">
            <el-skeleton :loading="true" animated>
              <template #template>
                <div style="display: flex; gap: 20px; padding: 0 20px;">
                  <el-skeleton-item variant="text" style="width: 50px; height: 16px;" />
                  <el-skeleton-item variant="text" style="width: 120px; height: 16px;" />
                  <el-skeleton-item variant="text" style="width: 100px; height: 16px;" />
                  <el-skeleton-item variant="text" style="width: 80px; height: 16px;" />
                </div>
              </template>
            </el-skeleton>
          </div>
        </div>
        <div v-else class="empty-state">
          <svg class="empty-icon" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="8" y="12" width="48" height="40" rx="4" stroke="#cbd5e1" stroke-width="2"/>
            <line x1="8" y1="24" x2="56" y2="24" stroke="#cbd5e1" stroke-width="2"/>
            <line x1="24" y1="12" x2="24" y2="52" stroke="#cbd5e1" stroke-width="2"/>
            <circle cx="32" cy="38" r="6" stroke="#cbd5e1" stroke-width="2"/>
            <line x1="32" y1="35" x2="32" y2="41" stroke="#cbd5e1" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          <p class="empty-text">{{ emptyText }}</p>
        </div>
      </template>
    </el-table>
    <div class="pagination-wrap">
      <el-pagination
        :current-page="page"
        :page-size="size"
        :total="total"
        :page-sizes="pageSizes"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="emit('update:page', $event)"
        @size-change="emit('update:size', $event)"
      />
    </div>
  </div>
</template>

<script setup>
defineProps({
  loading: Boolean,
  page: Number,
  size: Number,
  total: Number,
  pageSizes: { type: Array, default: () => [10, 20, 50] },
  emptyText: { type: String, default: '暂无数据' },
})
const emit = defineEmits(['update:page', 'update:size'])
</script>

<style scoped>
.table-wrapper {
  padding: 0;
}
.custom-table {
  width: 100%;
  --el-table-border-color: #f1f5f9;
  --el-table-header-bg-color: #f8fafc;
}
.custom-table :deep(th.el-table__cell) {
  font-weight: 600;
  color: #475569;
  background-color: #f8fafc;
  font-size: 13px;
}
.custom-table :deep(.el-table__row) {
  transition: background-color 0.2s;
}
.custom-table :deep(.el-table__row:hover) {
  background-color: #f1f5f9 !important;
}
.custom-table :deep(.el-table__empty-block) {
  min-height: 200px;
}

.skeleton-rows {
  padding: 8px 0;
}
.skeleton-row {
  padding: 16px 0;
  border-bottom: 1px solid #f0f2f5;
}
.skeleton-row:last-child {
  border-bottom: none;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
}

.empty-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-text {
  margin: 0;
  font-size: 14px;
  color: #94a3b8;
}
.pagination-wrap {
  display: flex;
  justify-content: center;
  padding: 16px 24px;
  border-top: 1px solid #f1f5f9;
}

@media (max-width: 600px) {
  .pagination-wrap {
    padding: 12px 8px;
    flex-wrap: wrap;
    gap: 8px;
  }
  .pagination-wrap :deep(.el-pagination) {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
