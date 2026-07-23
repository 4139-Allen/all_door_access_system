<template>
  <div class="not-found">
    <div class="code">404</div>
    <h1 class="title">页面未找到</h1>
    <p class="desc">您访问的页面不存在或已被移除</p>
    <el-button type="primary" @click="goHome">返回首页</el-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
const goHome = () => {
  if (!localStorage.getItem('token')) {
    router.push('/login')
    return
  }
  router.push('/user/dashboard')
}
</script>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: #f5f7fa;
}
.code {
  font-size: 80px;
  font-weight: 700;
  color: #dcdfe6;
  line-height: 1;
  margin-bottom: 16px;
}
.title {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}
.desc {
  margin: 0 0 24px;
  font-size: 14px;
  color: #909399;
}
</style>
