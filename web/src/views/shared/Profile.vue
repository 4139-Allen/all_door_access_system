<template>
  <div class="profile-page">
    <div class="page-header">
      <div class="header-left">
        <div>
          <h2 class="header-title">个人中心</h2>
          <p class="header-desc">管理您的个人信息和账户安全</p>
        </div>
      </div>
    </div>

    <div class="profile-content">
      <!-- 左侧：头像卡片 -->
      <div class="profile-card avatar-card">
        <div class="avatar-wrapper" @click="previewVisible = true">
          <img v-if="avatarUrl" :src="resolveAvatar(avatarUrl)" class="avatar-img" />
          <div v-else class="avatar-placeholder">
            <span>{{ username.charAt(0).toUpperCase() }}</span>
          </div>
          <div class="avatar-overlay">
            <el-icon :size="24"><ZoomIn /></el-icon>
            <span>查看头像</span>
          </div>
        </div>
        <el-button class="upload-btn" @click="triggerUpload">
          <el-icon><Upload /></el-icon>
          更换头像
        </el-button>
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          style="display: none"
          @change="handleFileChange"
        />
        <p class="avatar-hint">支持 JPG、PNG、GIF、WebP，最大 1MB</p>
      </div>

      <!-- 头像预览弹窗 -->
      <el-dialog v-model="previewVisible" width="min(400px, 90vw)" top="8vh" title="头像预览">
        <div class="preview-container">
          <img v-if="avatarUrl" :src="resolveAvatar(avatarUrl)" class="preview-img" />
          <div v-else class="preview-placeholder">
            <span>{{ username.charAt(0).toUpperCase() }}</span>
          </div>
        </div>
      </el-dialog>

      <!-- 右侧：信息 + 密码 -->
      <div class="profile-right">
        <!-- 基本信息 -->
        <div class="profile-card">
          <h3 class="card-title">基本信息</h3>
          <el-form label-width="80px" class="profile-form">
            <el-form-item label="用户名">
              <div class="username-row">
                <el-input
                  v-model="profileForm.username"
                  placeholder="请输入用户名"
                  :disabled="!editingUsername"
                  maxlength="30"
                />
                <el-button
                  v-if="!editingUsername"
                  type="primary"
                  text
                  @click="editingUsername = true"
                >
                  编辑
                </el-button>
                <template v-else>
                  <el-button type="primary" :loading="savingUsername" @click="saveUsername">
                    保存
                  </el-button>
                  <el-button @click="cancelEditUsername">取消</el-button>
                </template>
              </div>
            </el-form-item>
            <el-form-item label="角色">
              <el-tag :type="profile.role === 'admin' ? 'danger' : profile.role === 'operator' ? 'warning' : 'info'" effect="plain">
                {{ profile.role_name || profile.role }}
              </el-tag>
            </el-form-item>
            <el-form-item label="注册时间">
              <span class="time-text">{{ profile.created_at }}</span>
            </el-form-item>
          </el-form>
        </div>

        <!-- 绑定手机号 -->
        <div class="profile-card">
          <h3 class="card-title">绑定手机号</h3>
          <el-form label-width="80px" class="profile-form">
            <el-form-item label="手机号">
              <template v-if="!editingPhone">
                <span v-if="profile.phone" class="time-text">{{ profile.phone }}</span>
                <span v-else class="time-text bind-empty">未绑定</span>
                <el-button v-if="profile.phone" type="danger" text @click="handleUnbind('phone')">解绑</el-button>
                <el-button type="primary" text @click="startEditPhone">{{ profile.phone ? '更换' : '绑定' }}</el-button>
              </template>
              <template v-else>
                <div class="bind-edit">
                  <el-input v-model="bindPhone" placeholder="请输入手机号" maxlength="11" size="small" style="width:160px" />
                  <el-input v-model="bindCode" placeholder="验证码" maxlength="8" size="small" style="width:120px" />
                  <el-button size="small" plain :disabled="bindCooldown > 0" @click="sendBindCode('phone')">
                    {{ bindCooldown > 0 ? `${bindCooldown}s` : '获取验证码' }}
                  </el-button>
                  <el-button size="small" type="primary" :loading="bindLoading" @click="confirmBind('phone')">保存</el-button>
                  <el-button size="small" @click="cancelEditPhone">取消</el-button>
                </div>
              </template>
            </el-form-item>
          </el-form>
        </div>

        <!-- 绑定邮箱 -->
        <div class="profile-card">
          <h3 class="card-title">绑定邮箱</h3>
          <el-form label-width="80px" class="profile-form">
            <el-form-item label="邮箱">
              <template v-if="!editingEmail">
                <span v-if="profile.email" class="time-text">{{ profile.email }}</span>
                <span v-else class="time-text bind-empty">未绑定</span>
                <el-button v-if="profile.email" type="danger" text @click="handleUnbind('email')">解绑</el-button>
                <el-button type="primary" text @click="startEditEmail">{{ profile.email ? '更换' : '绑定' }}</el-button>
              </template>
              <template v-else>
                <div class="bind-edit">
                  <el-input v-model="bindEmail" placeholder="请输入邮箱" size="small" style="width:200px" />
                  <el-input v-model="bindCode" placeholder="验证码" maxlength="8" size="small" style="width:120px" />
                  <el-button size="small" plain :disabled="bindCooldown > 0" @click="sendBindCode('email')">
                    {{ bindCooldown > 0 ? `${bindCooldown}s` : '获取验证码' }}
                  </el-button>
                  <el-button size="small" type="primary" :loading="bindLoading" @click="confirmBind('email')">保存</el-button>
                  <el-button size="small" @click="cancelEditEmail">取消</el-button>
                </div>
              </template>
            </el-form-item>
          </el-form>
        </div>

        <!-- 修改密码 -->
        <div class="profile-card">
          <h3 class="card-title">{{ hasPassword ? '修改密码' : '设置密码' }}</h3>
          <el-form
            ref="pwdFormRef"
            :model="pwdForm"
            :rules="pwdRules"
            label-width="80px"
            class="profile-form"
          >
            <el-form-item v-if="hasPassword" label="原密码" prop="old_password">
              <el-input
                v-model="pwdForm.old_password"
                type="password"
                placeholder="请输入原密码"
                show-password
              />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="pwdForm.new_password"
                type="password"
                :placeholder="hasPassword ? '请输入新密码（6-20位）' : '请设置密码（6-20位）'"
                show-password
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input
                v-model="pwdForm.confirm_password"
                type="password"
                placeholder="请再次输入新密码"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingPwd" @click="savePassword">
                {{ hasPassword ? '修改密码' : '设置密码' }}
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Camera, ZoomIn, Upload } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { closeWebSocket } from '@/services/websocket'

const router = useRouter()
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const username = ref(localStorage.getItem('username') || '用户')
const avatarUrl = ref('')

const resolveAvatar = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return API_BASE + path
}
const fileInput = ref(null)
const pwdFormRef = ref(null)
const previewVisible = ref(false)

const hasPassword = ref(true)

const profile = reactive({
  id: null,
  username: '',
  role: '',
  avatar: '',
  created_at: ''
})

const profileForm = reactive({
  username: ''
})
const editingUsername = ref(false)
const savingUsername = ref(false)
const originalUsername = ref('')

const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})
const savingPwd = ref(false)

const validateConfirm = (rule, value, callback) => {
  if (!value) callback(new Error('请确认新密码'))
  else if (value !== pwdForm.new_password) callback(new Error('两次密码不一致'))
  else callback()
}

const pwdRules = ref({
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码为6-20位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, validator: validateConfirm, trigger: 'blur' }
  ]
})

// 加载个人信息
const loadProfile = async () => {
  try {
    const res = await request.get('/auth/profile')
    if (res.success) {
      Object.assign(profile, res.data)
      profileForm.username = res.data.username
      originalUsername.value = res.data.username
      username.value = res.data.username
      hasPassword.value = res.data.has_password !== false
      if (res.data.avatar) {
        avatarUrl.value = res.data.avatar
      }
    }
  } catch (e) {
    console.error('获取个人信息失败', e)
  }
}

// 头像上传
const triggerUpload = () => {
  fileInput.value?.click()
}

const handleFileChange = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  // 前端校验
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('仅支持 JPG、PNG、GIF、WebP 格式')
    e.target.value = ''
    return
  }
  if (file.size > 1 * 1024 * 1024) {
    ElMessage.error('头像文件大小不能超过 1MB')
    e.target.value = ''
    return
  }

  const formData = new FormData()
  formData.append('file', file)

  try {
    const res = await request.put('/auth/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (res.success) {
      avatarUrl.value = res.data.avatar
      localStorage.setItem('avatar', res.data.avatar)
      window.dispatchEvent(new Event('avatar-updated'))
      ElMessage.success('头像更新成功')
    } else {
      ElMessage.error(res.msg || '上传失败')
    }
  } catch (err) {
    ElMessage.error('网络错误，请稍后重试')
  }

  e.target.value = ''
}

// 修改用户名
const saveUsername = async () => {
  if (!profileForm.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (profileForm.username === originalUsername.value) {
    editingUsername.value = false
    return
  }

  savingUsername.value = true
  try {
    const res = await request.put('/auth/profile', { username: profileForm.username.trim() })
    if (res.success) {
      ElMessage.success('用户名修改成功')
      originalUsername.value = profileForm.username.trim()
      username.value = profileForm.username.trim()
      profile.username = profileForm.username.trim()
      localStorage.setItem('username', profileForm.username.trim())
      editingUsername.value = false
    } else {
      ElMessage.error(res.msg || '修改失败')
    }
  } catch (e) {
    ElMessage.error('网络错误，请稍后重试')
  } finally {
    savingUsername.value = false
  }
}

const cancelEditUsername = () => {
  profileForm.username = originalUsername.value
  editingUsername.value = false
}

// 修改密码
const savePassword = async () => {
  if (!pwdFormRef.value) return
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return

  savingPwd.value = true
  try {
    const payload = { new_password: pwdForm.new_password }
    if (hasPassword.value) payload.old_password = pwdForm.old_password
    const res = await request.put('/auth/password', payload)
    if (res.success) {
      ElMessage.success(hasPassword.value ? '密码修改成功，请重新登录' : '密码设置成功，请重新登录')
      hasPassword.value = true
      pwdForm.old_password = ''
      pwdForm.new_password = ''
      pwdForm.confirm_password = ''
      pwdFormRef.value?.clearValidate()
      setTimeout(() => {
        closeWebSocket()
        localStorage.clear()
        router.push('/login')
      }, 500)
    } else {
      ElMessage.error(res.msg || '修改失败')
    }
  } catch (e) {
    ElMessage.error('网络错误，请稍后重试')
  } finally {
    savingPwd.value = false
  }
}

// ======== 绑定手机号/邮箱 ========
const editingPhone = ref(false)
const editingEmail = ref(false)
const bindPhone = ref('')
const bindEmail = ref('')
const bindCode = ref('')
const bindLoading = ref(false)
const bindCooldown = ref(0)
let bindTimer = null

const startEditPhone = () => {
  bindPhone.value = profile.phone || ''
  bindCode.value = ''
  editingPhone.value = true
}
const cancelEditPhone = () => {
  editingPhone.value = false
  bindPhone.value = ''
  bindCode.value = ''
  clearInterval(bindTimer)
  bindCooldown.value = 0
}
const startEditEmail = () => {
  bindEmail.value = profile.email || ''
  bindCode.value = ''
  editingEmail.value = true
}
const cancelEditEmail = () => {
  editingEmail.value = false
  bindEmail.value = ''
  bindCode.value = ''
  clearInterval(bindTimer)
  bindCooldown.value = 0
}

const sendBindCode = async (type) => {
  const target = type === 'phone' ? bindPhone.value.trim() : bindEmail.value.trim()
  if (!target) { ElMessage.warning('请先输入' + (type === 'phone' ? '手机号' : '邮箱')); return }
  const valid = type === 'phone' ? /^1[3-9]\d{9}$/.test(target) : /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(target)
  if (!valid) { ElMessage.warning(type === 'phone' ? '请输入正确的手机号' : '请输入正确的邮箱地址'); return }
  try {
    const res = await request.post('/auth/send-code', { target })
    if (res.success) {
      ElMessage.success(res.msg)
      bindCooldown.value = 60
      bindTimer = setInterval(() => {
        bindCooldown.value--
        if (bindCooldown.value <= 0) clearInterval(bindTimer)
      }, 1000)
    } else { ElMessage.error(res.msg || '发送失败') }
  } catch (e) { ElMessage.error(e.response?.data?.msg || '发送失败') }
}

const confirmBind = async (type) => {
  if (!bindCode.value) { ElMessage.warning('请输入验证码'); return }
  const target = type === 'phone' ? bindPhone.value.trim() : bindEmail.value.trim()
  if (!target) { ElMessage.warning('请输入' + (type === 'phone' ? '手机号' : '邮箱')); return }
  bindLoading.value = true
  try {
    const payload = type === 'phone'
      ? { phone: target, code: bindCode.value }
      : { email: target, code: bindCode.value }
    const res = await request.put(type === 'phone' ? '/auth/bind-phone' : '/auth/bind-email', payload)
    if (res.success) {
      ElMessage.success(type === 'phone' ? '手机号绑定成功' : '邮箱绑定成功')
      cancelEditPhone(); cancelEditEmail()
      loadProfile()
    } else { ElMessage.error(res.msg || '绑定失败') }
  } catch (e) { ElMessage.error(e.response?.data?.msg || '绑定失败') }
  finally { bindLoading.value = false }
}

const handleUnbind = async (type) => {
  try {
    const res = await request.delete(`/auth/bind-${type}`)
    if (res.success) { ElMessage.success('解绑成功'); loadProfile() }
    else { ElMessage.error(res.msg || '解绑失败') }
  } catch (e) { ElMessage.error(e.response?.data?.msg || '解绑失败') }
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.profile-page {
  padding: 4px;
}

.profile-content {
  display: flex;
  gap: 20px;
  margin-top: 20px;
}

/* 卡片 */
.profile-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 24px;
}

.card-title {
  margin: 0 0 20px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f2f5;
}

/* 头像卡片 */
.avatar-card {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 32px;
}

.avatar-wrapper {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  border: 3px solid #e4e7ed;
  transition: border-color 0.2s;
}

.avatar-wrapper:hover {
  border-color: #6366f1;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #6366f1, #818cf8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  font-weight: 600;
  color: #fff;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #fff;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.avatar-hint {
  margin-top: 16px;
  font-size: 12px;
  color: #909399;
  text-align: center;
}

.upload-btn {
  margin-top: 16px;
}

/* 预览弹窗 */
.preview-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px;
}

.preview-img {
  max-width: 100%;
  max-height: 60vh;
  border-radius: 8px;
  object-fit: contain;
}

.preview-placeholder {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #818cf8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 72px;
  font-weight: 600;
  color: #fff;
}

/* 绑定手机号/邮箱 */
.bind-empty { color: #c0c4cc; }
.bind-edit { display: flex; gap: 8px; flex-wrap: wrap; }

/* 右侧 */
.profile-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

.profile-form {
  max-width: 480px;
}

.username-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.username-row .el-input {
  flex: 1;
}

.time-text {
  font-size: 14px;
  color: #606266;
}

/* 响应式 */
@media (max-width: 768px) {
  .profile-content {
    flex-direction: column;
  }

  .avatar-card {
    width: 100%;
  }
}
</style>
