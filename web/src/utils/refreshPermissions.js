/**
 * 权限刷新工具
 * 调用 GET /auth/permissions 刷新当前用户的权限并更新 localStorage
 * 用于管理员修改角色权限后主动同步，避免重新登录
 */
import request from '@/utils/request'

export async function refreshPermissions() {
  try {
    const res = await request.get('/auth/permissions')
    if (res.success && Array.isArray(res.data?.permissions)) {
      localStorage.setItem('permissions', JSON.stringify(res.data.permissions))
    }
    return res.data?.permissions || []
  } catch {
    // 静默失败 — 权限刷新失败不应阻塞用户操作
    return []
  }
}
