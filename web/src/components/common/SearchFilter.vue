<template>
  <div class="filter-form">
    <el-input
      v-model="filterForm[field]"
      :placeholder="placeholder"
      clearable
      size="default"
      class="search-input"
      @input="onInput"
      @keydown.enter="search"
    >
      <template #append>
        <el-button class="search-btn" @click="search">搜索</el-button>
      </template>
    </el-input>
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
const emit = defineEmits(['search'])

const onInput = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => emit('search'), 300)
}
const search = () => emit('search')

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
