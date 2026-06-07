import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

const service = axios.create({
  baseURL: API_BASE ? `${API_BASE}/api` : '/api',
  timeout: 15000
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  }
)

// 响应拦截
service.interceptors.response.use(
  (res) => res.data,
  (error) => {
    // 被主动取消的请求（页面切换、组件卸载），不处理
    if (axios.isCancel(error)) {
      return Promise.reject(error)
    }

    if (error.response) {
      const status = error.response.status

      if (status === 401) {
        ElMessage.error('登录已过期，请重新登录')
        localStorage.removeItem('token')
        localStorage.removeItem('user_id')
        localStorage.removeItem('role')
        localStorage.removeItem('role_name')
        localStorage.removeItem('permissions')
        router.push('/login')
      } else if (status === 403) {
        ElMessage.error('无权限访问')
      } else if (status === 404) {
        ElMessage.error('请求的资源不存在')
      } else if (status === 429) {
        ElMessage.warning(error.response.data?.msg || '请求过于频繁，请稍后再试')
      } else if (status >= 500) {
        ElMessage.error('服务器错误，请稍后重试')
      }
    } else {
      ElMessage.error('网络连接失败，请检查网络')
    }

    return Promise.reject(error)
  }
)

export default service
