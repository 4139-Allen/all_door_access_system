App({
  onLaunch() {
    // 检查登录态
    const token = wx.getStorageSync('token')
    if (token) {
      this.globalData.isLoggedIn = true
      this.globalData.token = token
      this.globalData.role = wx.getStorageSync('role') || ''
      this.globalData.username = wx.getStorageSync('username') || ''
    }
  },

  globalData: {
    isLoggedIn: false,
    token: '',
    role: '',
    username: ''
  }
})
