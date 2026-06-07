<template>
  <div class="filter-form">
    <el-input
      v-model="filterForm[field]"
      :placeholder="placeholder"
      clearable
      size="default"
      @input="onInput"
      @keydown.enter="search"
    />
    <el-button type="primary" @click="search">搜索</el-button>
    <el-button @click="reset">重置</el-button>
  </div>
</template>

<script setup>
import { onUnmounted } from 'vue'

let debounceTimer = null

defineProps({
  filterForm: { type: Object, required: true },
  field: { type: String, required: true },
  placeholder: { type: String, default: '搜索' },
})
const emit = defineEmits(['search', 'reset'])

const onInput = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => emit('search'), 300)
}
const search = () => emit('search')
const reset = () => {
  clearTimeout(debounceTimer)
  emit('reset')
}

onUnmounted(() => clearTimeout(debounceTimer))
</script>

<style scoped>
.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
</style>
