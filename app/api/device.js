import { get, post, put, del } from './request'

export const getDevices = (params) => {
  const query = new URLSearchParams()
  if (params.page) query.append('page', params.page)
  if (params.size) query.append('size', params.size)
  if (params.name) query.append('name', params.name)
  const qs = query.toString()
  return get('/api/devices' + (qs ? '?' + qs : ''))
}

export const createDevice = (data) => post('/api/devices', data)

export const updateDevice = (id, data) => put(`/api/devices/${id}`, data)

export const deleteDevice = (id) => del(`/api/devices/${id}`)

export const bindUserDevice = (deviceId, userId) => post(`/api/devices/${deviceId}/bind`, { user_id: userId })

export const unbindUserDevice = (deviceId, userId) => del(`/api/devices/${deviceId}/unbind?user_id=${userId}`)
