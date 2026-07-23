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
          <div class="bind-row">
            <span v-if="profile.phone" class="bind-value">{{ profile.phone }}</span>
            <span v-else class="bind-value bind-empty">未绑定</span>
            <el-button v-if="profile.phone" type="danger" text size="small" @click="handleUnbind('phone')">解绑</el-button>
            <el-button type="primary" text size="small" @click="showBindDialog('phone')">
              {{ profile.phone ? '更换' : '绑定' }}
            </el-button>
          </div>
        </div>

        <!-- 绑定邮箱 -->
        <div class="profile-card">
          <h3 class="card-title">绑定邮箱</h3>
          <div class="bind-row">
            <span v-if="profile.email" class="bind-value">{{ profile.email }}</span>
            <span v-else class="bind-value bind-empty">未绑定</span>
            <el-button v-if="profile.email" type="danger" text size="small" @click="handleUnbind('email')">解绑</el-button>
            <el-button type="primary" text size="small" @click="showBindDialog('email')">
              {{ profile.email ? '更换' : '绑定' }}
            </el-button>
          </div>
        </div>

        <!-- 绑定弹窗 -->
        <el-dialog v-model="bindDialogVisible" :title="bindDialogTitle" width="400px" :close-on-click-modal="false" @close="resetBindDialog">
          <el-form ref="bindFormRef" :model="bindForm" :rules="bindRules" label-width="0">
            <el-form-item prop="target">
              <el-input v-model="bindForm.target" :placeholder="bindType === 'phone' ? '请输入手机号' : '请输入邮箱地址'" :maxlength="bindType === 'phone' ? 11 : 50" />
            </el-form-item>
            <el-form-item prop="code">
              <div class="code-row">
                <el-input v-model="bindForm.code" placeholder="请输入验证码" maxlength="8" />
                <el-button type="primary" plain :disabled="bindCooldown > 0" @click="sendBindCode">
                  {{ bindCooldown > 0 ? `${bindCooldown}s` : '获取验证码' }}
                </el-button>
              </div>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="bindDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="bindLoading" @click="confirmBind">确认绑定</el-button>
          </template>
        </el-dialog>

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
import { ref, reactive, computed, onMounted } from 'vue'
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
const bindDialogVisible = ref(false)
const bindType = ref('phone')  // 'phone' | 'email'
const bindForm = reactive({ target: '', code: '' })
const bindFormRef = ref(null)
const bindLoading = ref(false)
const bindCooldown = ref(0)
let bindTimer = null

const bindDialogTitle = computed(() => {
  return bindType.value === 'phone' ? '绑定手机号' : '绑定邮箱'
})

const bindRules = computed(() => {
  if (bindType.value === 'phone') {
    return {
      target: [
        { required: true, message: '请输入手机号', trigger: 'blur' },
        { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
      ],
      code: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
    }
  }
  return {
    target: [
      { required: true, message: '请输入邮箱地址', trigger: 'blur' },
      { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
    ],
    code: [{ required: true, message: '请输入验证码', trigger: 'blur' }]
  }
})

const showBindDialog = (type) => {
  bindType.value = type
  bindForm.target = ''
  bindForm.code = ''
  bindDialogVisible.value = true
}

const resetBindDialog = () => {
  bindForm.target = ''
  bindForm.code = ''
  bindFormRef.value?.clearValidate()
  clearInterval(bindTimer)
  bindCooldown.value = 0
}

const sendBindCode = async () => {
  const target = bindForm.target.trim()
  if (!target) {
    ElMessage.warning('请先输入手机号或邮箱')
    return
  }
  const valid = bindType.value === 'phone'
    ? /^1[3-9]\d{9}$/.test(target)
    : /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(target)
  if (!valid) {
    ElMessage.warning(bindType.value === 'phone' ? '请输入正确的手机号' : '请输入正确的邮箱地址')
    return
  }
  try {
    const res = await request.post('/auth/send-code', { target })
    if (res.success) {
      ElMessage.success(res.msg)
      bindCooldown.value = 60
      bindTimer = setInterval(() => {
        bindCooldown.value--
        if (bindCooldown.value <= 0) clearInterval(bindTimer)
      }, 1000)
    } else {
      ElMessage.error(res.msg || '发送失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || '发送失败')
  }
}

const confirmBind = async () => {
  if (!bindFormRef.value) return
  const valid = await bindFormRef.value.validate().catch(() => false)
  if (!valid) return

  bindLoading.value = true
  try {
    let res
    if (bindType.value === 'phone') {
      res = await request.put('/auth/bind-phone', { phone: bindForm.target.trim(), code: bindForm.code })
    } else {
      res = await request.put('/auth/bind-email', { email: bindForm.target.trim(), code: bindForm.code })
    }
    if (res.success) {
      ElMessage.success(res.msg || '绑定成功')
      bindDialogVisible.value = false
      loadProfile()
    } else {
      ElMessage.error(res.msg || '绑定失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || '绑定失败')
  } finally {
    bindLoading.value = false
  }
}

const handleUnbind = async (type) => {
  const label = type === 'phone' ? '手机号' : '邮箱'
  try {
    const res = await request.delete(`/auth/bind-${type}`)
    if (res.success) {
      ElMessage.success(`${label}解绑成功`)
      loadProfile()
    } else {
      ElMessage.error(res.msg || '解绑失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || '解绑失败')
  }
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
.bind-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.bind-value {
  font-size: 14px;
  color: #303133;
}
.bind-empty {
  color: #c0c4cc;
}

/* 绑定弹窗验证码 */
.code-row {
  display: flex;
  gap: 12px;
}
.code-row .el-input {
  flex: 1;
}

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
