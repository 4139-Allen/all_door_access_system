const { BASE_URL } = require('./config')

/**
 * 封装 wx.request，自动带上 X-Token header
 */
function request(method, url, data) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token') || ''

    wx.request({
      url: BASE_URL + url,
      method: method,
      data: data,
      header: {
        'Content-Type': 'application/json',
        'X-Token': token
      },
      timeout: 15000,
      success(res) {
        // 401 未授权 → 清除登录态，跳转登录页
        if (res.statusCode === 401) {
          wx.removeStorageSync('token')
          wx.removeStorageSync('role')
          wx.removeStorageSync('username')
          const app = getApp()
          if (app) {
            app.globalData.isLoggedIn = false
            app.globalData.token = ''
          }
          wx.redirectTo({ url: '/pages/login/login' })
          reject(new Error('登录已过期'))
          return
        }

        const body = res.data
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(body)
        } else {
          wx.showToast({ title: body.msg || '请求失败', icon: 'none' })
          reject(new Error(body.msg || '请求失败'))
        }
      },
      fail(err) {
        wx.showToast({ title: '网络错误', icon: 'none' })
        reject(err)
      }
    })
  })
}

module.exports = {
  get: (url, data) => request('GET', url, data),
  post: (url, data) => request('POST', url, data),
  put: (url, data) => request('PUT', url, data),
  delete: (url, data) => request('DELETE', url, data)
}
