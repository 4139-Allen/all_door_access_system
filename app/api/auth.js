import { post, put } from './request'

export const login = (data) => post('/api/auth/login', data)

export const register = (data) => post('/api/auth/register', data)

export const logout = () => post('/api/auth/logout')

export const changePassword = (data) => put('/api/auth/password', data)
