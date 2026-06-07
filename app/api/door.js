import { get, post } from './request'

export const openDoor = (deviceId) => post(`/api/doors/${deviceId}/open`)

export const getDoorLogs = (params) => {
  const query = new URLSearchParams()
  if (params.page) query.append('page', params.page)
  if (params.size) query.append('size', params.size)
  if (params.device_name) query.append('device_name', params.device_name)
  if (params.status) query.append('status', params.status)
  if (params.start_time) query.append('start_time', params.start_time)
  if (params.end_time) query.append('end_time', params.end_time)
  const qs = query.toString()
  return get('/api/door-logs' + (qs ? '?' + qs : ''))
}
