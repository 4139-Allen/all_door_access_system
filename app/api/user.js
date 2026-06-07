import { get, post, del } from './request'

export const getUsers = (params) => {
  const query = new URLSearchParams()
  if (params.page) query.append('page', params.page)
  if (params.size) query.append('size', params.size)
  if (params.username) query.append('username', params.username)
  if (params.role) query.append('role', params.role)
  const qs = query.toString()
  return get('/api/users' + (qs ? '?' + qs : ''))
}

export const createUser = (data) => post('/api/users', data)

export const deleteUser = (userId) => del(`/api/users/${userId}`)

export const getUserDevices = (userId) => get(`/api/users/${userId}/devices`)
