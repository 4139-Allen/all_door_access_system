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