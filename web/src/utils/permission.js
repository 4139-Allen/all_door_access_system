/**
 * 权限工具函数
 * 从 localStorage 读取登录时存储的 permissions 列表进行判断
 */

// 拥有以下任一权限的用户，路由前缀使用 /admin（管理区域）
const ADMIN_AREA_PERMS = [
  'user.view', 'user.manage',
  'device.view', 'device.create', 'device.edit', 'device.delete', 'device.bind',
  'log.view', 'log.export',
]

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

/**
 * 是否属于管理区域（决定路由前缀用 /admin 还是 /user）
 * @returns {boolean}
 */
export function isAdminArea() {
  return hasAnyPermission(...ADMIN_AREA_PERMS)
}
