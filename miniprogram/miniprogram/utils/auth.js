/**
 * 登录态管理
 */

function isLoggedIn() {
  return !!wx.getStorageSync('token')
}

function getToken() {
  return wx.getStorageSync('token') || ''
}

function saveLoginInfo(token, role, username, permissions, roleName, userId) {
  wx.setStorageSync('token', token)
  wx.setStorageSync('user_id', userId || '')
  wx.setStorageSync('role', role || '')
  wx.setStorageSync('username', username || '')
  wx.setStorageSync('permissions', permissions || [])
  wx.setStorageSync('role_name', roleName || '')

  const app = getApp()
  if (app) {
    app.globalData.isLoggedIn = true
    app.globalData.token = token
    app.globalData.userId = userId || ''
    app.globalData.role = role || ''
    app.globalData.username = username || ''
    app.globalData.permissions = permissions || []
    app.globalData.roleName = roleName || ''
  }
}

function clearLoginInfo() {
  wx.removeStorageSync('token')
  wx.removeStorageSync('user_id')
  wx.removeStorageSync('role')
  wx.removeStorageSync('username')
  wx.removeStorageSync('permissions')
  wx.removeStorageSync('role_name')

  const app = getApp()
  if (app) {
    app.globalData.isLoggedIn = false
    app.globalData.token = ''
    app.globalData.userId = ''
    app.globalData.role = ''
    app.globalData.username = ''
    app.globalData.permissions = []
    app.globalData.roleName = ''
  }
}

function hasPermission(code) {
  const perms = wx.getStorageSync('permissions') || []
  return perms.includes(code)
}

function checkLogin() {
  if (!isLoggedIn()) {
    wx.redirectTo({ url: '/pages/login/login' })
    return false
  }
  return true
}

module.exports = {
  isLoggedIn,
  getToken,
  saveLoginInfo,
  clearLoginInfo,
  checkLogin,
  hasPermission
}
