import { ElMessage } from 'element-plus'
import { useDeviceStatus } from '@/composables/useDeviceStatus'
import { useDoorEventStream } from '@/composables/useDoorEventStream'

let ws = null
let lockReconnect = false
let retryCount = 0
let authFailed = false
const MAX_RETRY = 10

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

function createWebSocket() {
  const token = localStorage.getItem('token')
  if (!token) return

  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsHost = API_BASE ? API_BASE.replace(/^http/, 'ws') : `${wsProtocol}//${window.location.host}`
  const wsUrl = `${wsHost}/api/ws`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('✅ WebSocket 已连接！')
    retryCount = 0
    authFailed = false
    ws.send(JSON.stringify({ type: 'auth', token: localStorage.getItem('token') }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      if (data.type === 'auth') {
        if (data.status === 'ok') {
          console.log('✅ WebSocket 认证成功')
        } else {
          console.warn('❌ WebSocket 认证失败:', data.msg)
          authFailed = true
          ws.close()
        }
        return
      }

      if (data.type === 'door_open') {
        const { addDoorEvent } = useDoorEventStream()
        addDoorEvent(data)
      }

      if (data.type === 'device_status') {
        const { updateDeviceStatus } = useDeviceStatus()
        updateDeviceStatus(data.device_id, data.status)

        // 显示设备上下线通知
        if (data.status === 'online') {
          ElMessage.success(`设备 [${data.device_name}] 已上线`)
        } else if (data.status === 'offline') {
          ElMessage.warning(`设备 [${data.device_name}] 已离线`)
        }
        return
      }
    } catch (e) {
      console.log('消息解析失败', e)
    }
  }

  ws.onerror = () => reconnect()
  ws.onclose = () => {
    console.log('❌ WebSocket 断开')
    reconnect()
  }
}

function reconnect() {
  // 认证失败后不重连（避免死循环）
  if (authFailed) return
  if (lockReconnect) return
  if (retryCount >= MAX_RETRY) {
    console.log('WebSocket 重连已达上限')
    return
  }
  lockReconnect = true
  retryCount++
  // 指数退避: 1s, 2s, 4s, 8s... 最大 30s
  const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 30000)
  console.log(`WebSocket 重连中 (${retryCount}/${MAX_RETRY})，${delay}ms 后重试...`)
  setTimeout(() => {
    createWebSocket()
    lockReconnect = false
  }, delay)
}

export function initWebSocket() {
  createWebSocket()
}

export function closeWebSocket() {
  if (ws) {
    ws.close()
    ws = null
    authFailed = true  // 阻止自动重连
    lockReconnect = false
    retryCount = 0
  }
}

export default { initWebSocket, closeWebSocket }
