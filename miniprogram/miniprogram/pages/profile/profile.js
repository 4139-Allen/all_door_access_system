const api = require('../../utils/api')
const auth = require('../../utils/auth')

Page({
  data: {
    isLoggedIn: false,
    username: '',
    role: '',
    showPasswordModal: false,
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  },

  onShow() {
    const isLoggedIn = auth.isLoggedIn()
    const app = getApp()
    this.setData({
      isLoggedIn,
      username: app.globalData.username || wx.getStorageSync('username') || '',
      role: app.globalData.role || wx.getStorageSync('role') || ''
    })
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/login' })
  },

  showChangePassword() {
    this.setData({ showPasswordModal: true })
  },

  hideChangePassword() {
    this.setData({
      showPasswordModal: false,
      oldPassword: '',
      newPassword: '',
      confirmPassword: ''
    })
  },

  onOldPasswordInput(e) {
    this.setData({ oldPassword: e.detail.value })
  },

  onNewPasswordInput(e) {
    this.setData({ newPassword: e.detail.value })
  },

  onConfirmPasswordInput(e) {
    this.setData({ confirmPassword: e.detail.value })
  },

  changePassword() {
    const { oldPassword, newPassword, confirmPassword } = this.data

    if (!oldPassword || !newPassword || !confirmPassword) {
      wx.showToast({ title: '请填写所有字段', icon: 'none' })
      return
    }

    if (newPassword.length < 6) {
      wx.showToast({ title: '新密码至少6位', icon: 'none' })
      return
    }

    if (newPassword !== confirmPassword) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }

    api.put('/auth/password', {
      old_password: oldPassword,
      new_password: newPassword
    }).then(() => {
      wx.showToast({ title: '密码修改成功', icon: 'success' })
      this.hideChangePassword()
      // 密码修改后需要重新登录
      setTimeout(() => {
        this.logout()
      }, 1500)
    }).catch(() => {})
  },

  logout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          api.post('/auth/logout').catch(() => {})
          auth.clearLoginInfo()
          this.setData({
            isLoggedIn: false,
            username: '',
            role: ''
          })
          wx.showToast({ title: '已退出登录', icon: 'success' })
          setTimeout(() => {
            wx.redirectTo({ url: '/pages/login/login' })
          }, 500)
        }
      }
    })
  }
})
