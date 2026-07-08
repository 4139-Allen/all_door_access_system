import { BASE_URL } from '../utils/config'

function request(method, url, data) {
  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync('token') || ''
    uni.request({
      url: BASE_URL + url,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        'X-Token': token
      },
      timeout: 15000,
      success(res) {
        if (res.statusCode === 401) {
          uni.removeStorageSync('token')
          uni.removeStorageSync('role')
          uni.removeStorageSync('username')
          uni.reLaunch({ url: '/pages/login/login' })
          reject(new Error('未登录'))
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          // 从 Authorization 响应头提取 token（标准做法）
          const auth = res.header && (res.header['authorization'] || res.header['Authorization'])
          const body = res.data
          if (auth && auth.startsWith('Bearer ') && body) {
            body._token = auth.slice(7)
          }
          resolve(body)
        } else {
          uni.showToast({ title: res.data.msg || '请求失败', icon: 'none' })
          reject(res.data)
        }
      },
      fail(err) {
        uni.showToast({ title: '网络错误', icon: 'none' })
        reject(err)
      }
    })
  })
}

export const get = (url, data) => request('GET', url, data)
export const post = (url, data) => request('POST', url, data)
export const put = (url, data) => request('PUT', url, data)
export const del = (url, data) => request('DELETE', url, data)
