/**
 * 权限工具函数
 * 从 localStorage 读取登录时存储的 permissions 列表进行判断
 */

/**
 * 获取当前用户的权限列表
 * @returns {string[]} 权限 code 数组
 */
export function getPermissions() {
  try {
    return JSON.parse(localStorage.getItem('permissions') || '[]')
  } catch {
    return []
  }
}

/**
 * 是否拥有指定权限
 * @param {string} code 权限标识，如 "device.view"
 * @returns {boolean}
 */
export function hasPermission(code) {
  return getPermissions().includes(code)
}

/**
 * 是否拥有任意一个权限
 * @param  {...string} codes 权限标识列表
 * @returns {boolean}
 */
export function hasAnyPermission(...codes) {
  const perms = getPermissions()
  return codes.some(c => perms.includes(c))
}
