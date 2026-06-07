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
                  maxlength="50"
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
                :placeholder="hasPassword ? '请输入新密码（至少6位）' : '请设置密码（至少6位）'"
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
    { min: 6, message: '密码至少 6 位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, validator: validateConfirm, trigger: 'blur' }
  ]
})

// 加载个人信息
const loadProfile = async () => {
  try {
    const res = await request.get('/auth/profile')
    if (res.code === 200) {
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
    if (res.code === 200) {
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
    if (res.code === 200) {
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
    if (res.code === 200) {
      ElMessage.success(hasPassword.value ? '密码修改成功，请重新登录' : '密码设置成功，请重新登录')
      hasPassword.value = true
      pwdForm.old_password = ''
      pwdForm.new_password = ''
      pwdForm.confirm_password = ''
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
