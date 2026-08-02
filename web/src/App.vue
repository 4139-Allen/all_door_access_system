<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { initWebSocket } from '@/services/websocket'

// 项目一启动就建立 WebSocket 长连接 → 实时通知
onMounted(() => {
  initWebSocket()
})
</script>

<style>
/* 始终为滚动条预留位置：弹窗锁滚动时布局不跳动 */
html {
  scrollbar-gutter: stable;
}
</style>