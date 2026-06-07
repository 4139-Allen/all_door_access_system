<template>
  <form class="add-form" @submit.prevent="$emit('add')">
    <slot />
    <el-button type="primary" native-type="submit" :loading="loading">新增</el-button>
  </form>
</template>

<script setup>
defineProps({
  loading: { type: Boolean, default: false },
})
defineEmits(['add'])
</script>

<style scoped>
.add-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
</style>
