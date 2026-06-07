const api = require('../../utils/api')
const auth = require('../../utils/auth')

Page({
  data: {
    showPasswordForm: false,
    username: '',
    password: '',
    loading: false
  },

  toggleForm() {
    this.setData({ showPasswordForm: !this.data.showPasswordForm })
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  // 微信一键登录
  wxLogin() {
    this.setData({ loading: true })

    wx.login({
      success: (loginRes) => {
        if (!loginRes.code) {
          wx.showToast({ title: '微信登录失败', icon: 'none' })
          this.setData({ loading: false })
          return
        }

        api.post('/auth/wx-login', { code: loginRes.code })
          .then((res) => {
            auth.saveLoginInfo(res.data.token, res.data.role, res.data.username, res.data.permissions, res.data.role_name, res.data.user_id)
            wx.showToast({ title: '登录成功', icon: 'success' })
            setTimeout(() => {
              wx.switchTab({ url: '/pages/doors/doors' })
            }, 500)
          })
          .catch((err) => {
            console.error('登录失败:', err)
          })
          .finally(() => {
            this.setData({ loading: false })
          })
      },
      fail: () => {
        wx.showToast({ title: '微信登录失败', icon: 'none' })
        this.setData({ loading: false })
      }
    })
  },

  // 账号密码登录
  passwordLogin() {
    const { username, password } = this.data
    const trimmedUsername = username.trim()
    if (!trimmedUsername || !password) {
      wx.showToast({ title: '请输入用户名和密码', icon: 'none' })
      return
    }

    this.setData({ loading: true })

    api.post('/auth/login', { username: trimmedUsername, password })
      .then((res) => {
        auth.saveLoginInfo(res.data.token, res.data.role, trimmedUsername, res.data.permissions, res.data.role_name, res.data.user_id)
        wx.showToast({ title: '登录成功', icon: 'success' })
        setTimeout(() => {
          wx.switchTab({ url: '/pages/doors/doors' })
        }, 500)
      })
      .catch((err) => {
        console.error('登录失败:', err)
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  }
})
