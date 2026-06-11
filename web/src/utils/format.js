/**
 * 通用格式化工具函数
 */

/**
 * 状态简短显示（Tag 显示用）
 * 完整状态通过 Tooltip 展示
 * @param {string} status - 完整状态文本
 * @returns {string} 简短状态文本
 */
export const getShortStatus = (status) => {
  if (status === '成功') return '成功'
  if (status.includes('锁定')) return '设备锁定'
  if (status.includes('密码错误')) return '密码错误'
  if (status.includes('指纹不匹配')) return '指纹错误'
  if (status.includes('未授权卡片')) return '刷卡错误'
  if (status.includes('不在线')) return '设备离线'
  return '失败'
}

/**
 * 操作类型标签样式
 * @param {string} action - 操作文本
 * @returns {string} Element Plus Tag type
 */
export const getActionTagType = (action) => {
  if (action.includes('远程')) return 'primary'
  if (action.includes('密码')) return 'warning'
  if (action.includes('指纹')) return 'success'
  if (action.includes('刷卡')) return 'info'
  return 'danger'
}
