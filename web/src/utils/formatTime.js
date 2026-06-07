import { ref } from 'vue'

// 响应式 tick，每分钟 +1，驱动所有相对时间重新计算
const tick = ref(0)
let _timerStarted = false

/**
 * 启动相对时间自动刷新（全局只需调用一次）
 */
export function startRelativeTimeTick() {
  if (_timerStarted) return
  _timerStarted = true
  setInterval(() => { tick.value++ }, 60000)
}

/**
 * 将时间字符串转为相对时间描述
 * @param {string} timeStr - 格式 "YYYY-MM-DD HH:mm:ss"
 * @returns {string} "刚刚" / "3分钟前" / "2小时前" / "3天前" / 原始时间
 */
export function formatRelativeTime(timeStr) {
  if (!timeStr) return ''
  const date = new Date(timeStr.replace(/-/g, '/'))
  const diff = Math.floor((Date.now() - date.getTime()) / 1000)

  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  if (diff < 604800) return `${Math.floor(diff / 86400)}天前`
  return timeStr
}

/**
 * 响应式相对时间（依赖 tick，每分钟自动刷新）
 * @param {string} timeStr
 * @returns {string}
 */
export function useRelativeTime(timeStr) {
  // eslint-disable-next-line no-unused-expressions
  tick.value
  return formatRelativeTime(timeStr)
}
