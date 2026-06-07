const api = require('../../utils/api')
const auth = require('../../utils/auth')

Page({
  data: {
    isLoggedIn: false,
    canOpen: false,
    devices: [],
    loading: false,
    openingId: null,
    stats: null
  },

  onLoad() {
    this.checkLoginAndLoad()
  },

  onShow() {
    this.checkLoginAndLoad()
  },

  onPullDownRefresh() {
    Promise.all([this.loadDevices(), this.loadStats()]).finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  checkLoginAndLoad() {
    const isLoggedIn = auth.isLoggedIn()
    this.setData({
      isLoggedIn,
      canOpen: isLoggedIn && auth.hasPermission('door.open')
    })
    if (isLoggedIn) {
      this.loadDevices()
      this.loadStats()
    }
  },

  loadStats() {
    return api.get('/statistics')
      .then((res) => {
        this.setData({ stats: res.data })
      })
      .catch(() => {})
  },

  loadDevices() {
    this.setData({ loading: true })
    return api.get('/devices', { page: 1, size: 50 })
      .then((res) => {
        this.setData({
          devices: res.data.list || [],
          loading: false
        })
      })
      .catch(() => {
        this.setData({ loading: false })
      })
  },

  openDoor(e) {
    const { id, name } = e.currentTarget.dataset
    this.setData({ openingId: id })

    wx.showModal({
      title: '确认开门',
      content: `确定要打开「${name}」吗？`,
      success: (modalRes) => {
        if (modalRes.confirm) {
          api.post(`/doors/${id}/open`)
            .then((res) => {
              wx.showToast({ title: '开门成功', icon: 'success' })
              this.loadDevices()
            })
            .catch(() => {})
            .finally(() => {
              this.setData({ openingId: null })
            })
        } else {
          this.setData({ openingId: null })
        }
      },
      fail: () => {
        this.setData({ openingId: null })
      }
    })
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/login' })
  }
})
