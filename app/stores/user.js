export function getUsername() {
  return uni.getStorageSync('username') || ''
}

export function isLoggedIn() {
  return !!uni.getStorageSync('token')
}

export function isAdmin() {
  return uni.getStorageSync('role') === 'admin'
}

export function getRole() {
  return uni.getStorageSync('role') || ''
}

export function saveLoginInfo(token, role, username, permissions, roleName, userId) {
  uni.setStorageSync('token', token)
  uni.setStorageSync('user_id', userId || '')
  uni.setStorageSync('role', role)
  if (username) uni.setStorageSync('username', username)
  uni.setStorageSync('permissions', permissions || [])
  uni.setStorageSync('role_name', roleName || '')
}

export function clearLoginInfo() {
  uni.removeStorageSync('token')
  uni.removeStorageSync('user_id')
  uni.removeStorageSync('role')
  uni.removeStorageSync('username')
  uni.removeStorageSync('permissions')
  uni.removeStorageSync('role_name')
}

export function hasPermission(code) {
  const perms = uni.getStorageSync('permissions') || []
  return perms.includes(code)
}
