<template>
  <div class="login-page">
    <div class="login-card">
      <div class="header">
        <div class="icon-box">
          <el-icon class="lock-icon"><Lock /></el-icon>
        </div>
        <h1 class="title">智能门禁管理系统</h1>
        <p class="subtitle">智能识别 · 安全管控 · 高效管理</p>
      </div>

      <el-tabs v-model="activeTab" class="login-tabs">
        <!-- 登录 -->
        <el-tab-pane label="登录" name="login">
          <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" class="login-form" @submit.prevent="handleLogin">
            <!-- 统一凭据输入 -->
            <el-form-item prop="username">
              <div class="input-wrap" :class="{ focus: focusedField === 'username' }">
                <el-icon class="input-icon">
                  <Promotion v-if="loginMode === 'email'" />
                  <Iphone v-else-if="loginMode === 'phone'" />
                  <User v-else />
                </el-icon>
                <el-input v-model="loginForm.username" placeholder="手机号 / 邮箱 / 用户名" class="custom-input" @focus="focusedField = 'username'" @blur="focusedField = ''" clearable />
              </div>
            </el-form-item>

            <!-- 密码/验证码方式选择 -->

            <!-- 密码模式 -->
            <template v-if="authMode === 'password'">
              <el-form-item prop="password">
                <div class="input-wrap" :class="{ focus: focusedField === 'pwd' }">
                  <el-icon class="input-icon"><Lock /></el-icon>
                  <el-input v-model="loginForm.password" :type="loginPwdVisible ? 'text' : 'password'" placeholder="请输入密码" class="custom-input" @focus="focusedField = 'pwd'" @blur="focusedField = ''" />
                  <el-button text class="pwd-toggle" @click="loginPwdVisible = !loginPwdVisible">
                    <el-icon><View v-if="loginPwdVisible" /><Hide v-else /></el-icon>
                  </el-button>
                </div>
              </el-form-item>
              <!-- 密码模式需要数学验证码 -->
              <el-form-item v-if="authMode === 'password'" prop="captcha">
                <div class="captcha-row">
                  <span class="captcha-question" @click="refreshCaptcha">{{ loginCaptcha.text }}</span>
                  <el-input v-model="loginForm.captcha" placeholder="输入答案" class="captcha-input" />
                </div>
              </el-form-item>
            </template>

            <!-- 验证码模式（仅手机号/邮箱） -->
            <template v-if="authMode === 'code'">
              <el-form-item prop="code">
                <div class="code-row">
                  <div class="input-wrap" :class="{ focus: focusedField === 'code' }">
                    <el-icon class="input-icon"><Message /></el-icon>
                    <el-input v-model="loginForm.code" placeholder="请输入验证码" maxlength="8" class="custom-input" @focus="focusedField = 'code'" @blur="focusedField = ''" />
                  </div>
                  <el-button type="primary" plain :disabled="cooldown > 0" @click="sendCode" class="code-btn">
                    {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
                  </el-button>
                </div>
              </el-form-item>
            </template>

            <el-button type="primary" class="submit-btn" :loading="loginLoading" native-type="submit">登录</el-button>

            <div class="login-footer">
              <span class="footer-switch">
                <a :class="{ 'active-link': authMode === 'password' }" @click="switchTo('password')">密码登录</a>
                <span class="switch-divider">|</span>
                <a :class="{ 'active-link': authMode === 'code' }" @click="switchTo('code')">验证码登录</a>
              </span>
              <a class="forgot-link" @click="showForgotDialog = true">忘记密码？</a>
            </div>
          </el-form>
        </el-tab-pane>

        <!-- 注册 -->
        <el-tab-pane label="注册" name="register">
          <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" class="login-form" @submit.prevent="handleRegister">
            <el-form-item prop="username">
              <div class="input-wrap" :class="{ focus: focusedField === 'ru' }">
                <el-icon class="input-icon"><User /></el-icon>
                <el-input v-model="registerForm.username" placeholder="请输入用户名（1-30位）" maxlength="30" class="custom-input" @focus="focusedField = 'ru'" @blur="focusedField = ''" />
              </div>
            </el-form-item>
            <el-form-item prop="password">
              <div class="input-wrap" :class="{ focus: focusedField === 'rp' }">
                <el-icon class="input-icon"><Lock /></el-icon>
                <el-input v-model="registerForm.password" :type="regPwdVisible ? 'text' : 'password'" placeholder="6-20位密码" class="custom-input" @focus="focusedField = 'rp'" @blur="focusedField = ''" />
                <el-button text class="pwd-toggle" @click="regPwdVisible = !regPwdVisible">
                  <el-icon><View v-if="regPwdVisible" /><Hide v-else /></el-icon>
                </el-button>
              </div>
            </el-form-item>
            <el-form-item prop="confirmPassword">
              <div class="input-wrap" :class="{ focus: focusedField === 'rc' }">
                <el-icon class="input-icon"><Lock /></el-icon>
                <el-input v-model="registerForm.confirmPassword" :type="regConfirmVisible ? 'text' : 'password'" placeholder="请再次输入密码" class="custom-input" @focus="focusedField = 'rc'" @blur="focusedField = ''" />
                <el-button text class="pwd-toggle" @click="regConfirmVisible = !regConfirmVisible">
                  <el-icon><View v-if="regConfirmVisible" /><Hide v-else /></el-icon>
                </el-button>
              </div>
            </el-form-item>
            <el-form-item prop="captcha">
              <div class="captcha-row">
                <span class="captcha-question" @click="refreshRegCaptcha">{{ registerCaptcha.text }}</span>
                <el-input v-model="registerCaptchaAnswer" placeholder="输入答案" class="captcha-input" />
              </div>
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="registerLoading" native-type="submit">立即注册</el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div class="footer">v2.0 · 智能门禁管理系统</div>
    </div>

    <!-- 忘记密码弹窗 -->
    <el-dialog v-model="showForgotDialog" title="重置密码" width="420px" :close-on-click-modal="false" @close="resetForgotForm">
      <el-form ref="forgotFormRef" :model="forgotForm" :rules="forgotRules" class="login-form" label-width="0">
        <el-form-item prop="phone">
          <div class="input-wrap" :class="{ focus: focusedField === 'fph' }">
            <el-icon class="input-icon"><Iphone /></el-icon>
            <el-input v-model="forgotForm.phone" placeholder="请输入手机号" maxlength="11" class="custom-input" @focus="focusedField = 'fph'" @blur="focusedField = ''" />
          </div>
        </el-form-item>
        <el-form-item prop="code">
          <div class="code-row">
            <div class="input-wrap" :class="{ focus: focusedField === 'fcd' }">
              <el-icon class="input-icon"><Message /></el-icon>
              <el-input v-model="forgotForm.code" placeholder="请输入验证码" maxlength="8" class="custom-input" @focus="focusedField = 'fcd'" @blur="focusedField = ''" />
            </div>
            <el-button type="primary" plain :disabled="forgotCooldown > 0" @click="sendForgotCode" class="code-btn">
              {{ forgotCooldown > 0 ? `${forgotCooldown}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item prop="new_password">
          <div class="input-wrap" :class="{ focus: focusedField === 'fnp' }">
            <el-icon class="input-icon"><Lock /></el-icon>
            <el-input v-model="forgotForm.new_password" type="password" placeholder="6-20位新密码" show-password class="custom-input" @focus="focusedField = 'fnp'" @blur="focusedField = ''" />
          </div>
        </el-form-item>
        <el-form-item prop="confirm_password">
          <div class="input-wrap" :class="{ focus: focusedField === 'fcp' }">
            <el-icon class="input-icon"><Lock /></el-icon>
            <el-input v-model="forgotForm.confirm_password" type="password" placeholder="请再次输入新密码" show-password class="custom-input" @focus="focusedField = 'fcp'" @blur="focusedField = ''" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForgotDialog = false">取消</el-button>
        <el-button type="primary" :loading="forgotLoading" @click="handleResetPassword">重置密码</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, View, Hide, Iphone, Message, Promotion } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { initWebSocket } from '@/services/websocket'
import { isAdminArea } from '@/utils/permission'

const router = useRouter()
const activeTab = ref('login')
const focusedField = ref('')

// 焦点框由 CSS 的 :focus:not(:focus-visible) 控制

// 切换 tab 时清除对应表单的校验状态和数据
watch(activeTab, (tab) => {
  if (tab === 'login') {
    loginFormRef.value?.clearValidate()
    loginForm.value = { username: '', password: '', code: '', captcha: '' }
    authMode.value = 'password'
    refreshCaptcha()
  } else {
    registerFormRef.value?.clearValidate()
  }
})

// ======== 登录 ========
const loginLoading = ref(false)
const loginPwdVisible = ref(false)
const loginFormRef = ref(null)
const loginForm = ref({ username: '', password: '', code: '', captcha: '' })
const authMode = ref('password')      // 'password' | 'code'
const cooldown = ref(0)
let cooldownTimer = null

// 自动识别凭据类型
const loginMode = computed(() => {
  const v = loginForm.value.username.trim()
  if (/^1[3-9]\d{9}$/.test(v)) return 'phone'
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return 'email'
  return 'username'
})

// 切换密码/验证码模式
const switchTo = (mode) => {
  authMode.value = mode
}

// 登录表单校验规则（按模式动态生成）
const loginRules = computed(() => {
  const rules = {
    username: [{ required: true, message: '请输入手机号/邮箱/用户名', trigger: 'blur' }]
  }
  if (authMode.value === 'password') {
    rules.password = [{ required: true, message: '请输入密码', trigger: 'blur' }]
    rules.captcha = [{ required: true, message: '请输入验证码', trigger: 'blur' }]
  } else {
    rules.code = [{ required: true, message: '请输入验证码', trigger: 'blur' }]
  }
  return rules
})

// 由 footer-switch 的链接直接控制

// 数学验证码
const genCaptcha = () => {
  const a = Math.floor(Math.random() * 20) + 1
  const b = Math.floor(Math.random() * 20) + 1
  const op = Math.random() > 0.5 ? '+' : '-'
  const answer = op === '+' ? a + b : a - b
  return { text: `${a} ${op} ${b} = ?`, answer }
}
const loginCaptcha = ref(genCaptcha())
const registerCaptcha = ref(genCaptcha())
const registerCaptchaAnswer = ref('')
const refreshCaptcha = () => { loginCaptcha.value = genCaptcha() }
const refreshRegCaptcha = () => { registerCaptcha.value = genCaptcha() }

// 发送验证码
const sendCode = async () => {
  const target = loginForm.value.username.trim()
  if (!target) {
    ElMessage.warning('请先输入手机号或邮箱')
    return
  }
  const mode = loginMode.value
  if (mode === 'phone' && !/^1[3-9]\d{9}$/.test(target)) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (mode === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(target)) {
    ElMessage.warning('请输入正确的邮箱地址')
    return
  }
  try {
    const res = await request.post('/auth/send-code', { target })
    if (res.success) {
      ElMessage.success(res.msg || '验证码已发送')
      cooldown.value = 60
      cooldownTimer = setInterval(() => {
        cooldown.value--
        if (cooldown.value <= 0) clearInterval(cooldownTimer)
      }, 1000)
    } else {
      ElMessage.error(res.msg || '发送失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || '发送失败')
  }
}

// 登录
const handleLogin = async () => {
  if (!loginFormRef.value) return
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  const username = loginForm.value.username.trim()
  const mode = loginMode.value

  // 密码模式需要校验数学验证码
  if (authMode.value === 'password') {
    if (parseInt(loginForm.value.captcha) !== loginCaptcha.value.answer) {
      ElMessage.warning('验证码错误')
      refreshCaptcha()
      loginForm.value.captcha = ''
      return
    }
  }

  loginLoading.value = true
  try {
    let res
    if (authMode.value === 'code') {
      res = await request.post('/auth/login-code', { username, code: loginForm.value.code })
    } else {
      res = await request.post('/auth/login', { username, password: loginForm.value.password.trim() })
    }

    if (res.success) {
      handleLoginSuccess(res.data, res.token)
    } else {
      ElMessage.error(res.msg || '登录失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.msg || '登录失败')
  } finally {
    loginLoading.value = false
    if (authMode.value === 'password') {
      refreshCaptcha()
      loginForm.value.captcha = ''
    }
  }
}

// ======== 注册 ========
const registerLoading = ref(false)
const regPwdVisible = ref(false)
const regConfirmVisible = ref(false)
const registerFormRef = ref(null)
const registerForm = ref({ username: '', password: '', confirmPassword: '' })
const validateConfirm = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入密码'))
  else if (value !== registerForm.value.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}
const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_.\-一-龥]+$/, message: '用户名只能包含字母、数字、下划线、点和中划线', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码为6-20位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  const valid = await registerFormRef.value.validate().catch(() => false)
  if (!valid) return
  if (parseInt(registerCaptchaAnswer.value) !== registerCaptcha.value.answer) {
    ElMessage.warning('验证码错误')
    refreshRegCaptcha()
    registerCaptchaAnswer.value = ''
    return
  }
  registerLoading.value = true
  try {
    const res = await request.post('/auth/register', {
      ...registerForm.value,
      username: registerForm.value.username.trim(),
      password: registerForm.value.password.trim()
    })
    if (res.success) {
      ElMessage.success('注册成功，请登录')
      registerForm.value = { username: '', password: '', confirmPassword: '' }
      activeTab.value = 'login'
    } else {
      ElMessage.error(res.msg || '注册失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.msg || '注册失败')
  } finally {
    registerLoading.value = false
    refreshRegCaptcha()
    registerCaptchaAnswer.value = ''
  }
}

// ======== 忘记密码 ========
const showForgotDialog = ref(false)
const forgotLoading = ref(false)
const forgotFormRef = ref(null)
const forgotForm = ref({ phone: '', code: '', new_password: '', confirm_password: '' })
const forgotCooldown = ref(0)
let forgotTimer = null

const validateForgotConfirm = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入新密码'))
  else if (value !== forgotForm.value.new_password) callback(new Error('两次密码不一致'))
  else callback()
}
const forgotRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  code: [{ required: true, message: '请输入验证码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码为6-20位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateForgotConfirm, trigger: 'blur' }
  ]
}

const sendForgotCode = async () => {
  if (!forgotForm.value.phone || !/^1[3-9]\d{9}$/.test(forgotForm.value.phone)) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  try {
    const res = await request.post('/auth/send-code', { target: forgotForm.value.phone })
    if (res.success) {
      ElMessage.success(res.msg || '验证码已发送')
      forgotCooldown.value = 60
      forgotTimer = setInterval(() => {
        forgotCooldown.value--
        if (forgotCooldown.value <= 0) clearInterval(forgotTimer)
      }, 1000)
    } else {
      ElMessage.error(res.msg || '发送失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || '发送失败')
  }
}

const handleResetPassword = async () => {
  if (!forgotFormRef.value) return
  const valid = await forgotFormRef.value.validate().catch(() => false)
  if (!valid) return

  forgotLoading.value = true
  try {
    const res = await request.post('/auth/reset-password', {
      phone: forgotForm.value.phone,
      code: forgotForm.value.code,
      new_password: forgotForm.value.new_password.trim()
    })
    if (res.success) {
      ElMessage.success('密码重置成功，请登录')
      showForgotDialog.value = false
    } else {
      ElMessage.error(res.msg || '重置失败')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || '重置失败')
  } finally {
    forgotLoading.value = false
  }
}

const resetForgotForm = () => {
  forgotForm.value = { phone: '', code: '', new_password: '', confirm_password: '' }
  forgotFormRef.value?.clearValidate()
  clearInterval(forgotTimer)
  forgotCooldown.value = 0
}

// ======== 通用 ========
const handleLoginSuccess = (data, token) => {
  localStorage.setItem('token', token)
  localStorage.setItem('user_id', String(data.user_id || ''))
  localStorage.setItem('role', data.role)
  localStorage.setItem('role_name', data.role_name || data.role)
  localStorage.setItem('username', data.username || '')
  if (data.avatar) localStorage.setItem('avatar', data.avatar)
  localStorage.setItem('permissions', JSON.stringify(data.permissions || []))
  initWebSocket()
  ElMessage.success('登录成功')
  router.push(isAdminArea() ? '/admin/dashboard' : '/user/dashboard')
}

onUnmounted(() => {
  clearInterval(cooldownTimer)
  clearInterval(forgotTimer)
})
</script>

<style scoped>
.login-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f0f2f5;
}

.login-card {
  width: 420px;
  max-width: calc(100vw - 32px);
  padding: 40px 36px 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.header { text-align: center; margin-bottom: 28px; }
.icon-box { width: 48px; height: 48px; margin: 0 auto 16px; background: #409eff; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.lock-icon { font-size: 22px; color: #fff; }
.title { margin: 0 0 4px; font-size: 22px; font-weight: 600; color: #303133; }
.subtitle { margin: 0; font-size: 13px; color: #909399; }

.login-tabs :deep(.el-tabs__header) { margin-bottom: 22px; }
.login-tabs :deep(.el-tabs__item) { font-size: 13px; font-weight: 500; height: 36px; line-height: 36px; }
.login-tabs :deep(.el-tabs__item:focus:not(:focus-visible)) {
  outline: none;
  box-shadow: none;
}
.login-tabs :deep(.el-tabs__item:focus-visible) {
  outline: 2px solid #409eff;
  outline-offset: -2px;
}
.login-tabs :deep(.el-tabs__nav-wrap::after) { height: 0; }
.login-tabs :deep(.el-tabs__active-bar) { height: 2px; }

.login-form { display: flex; flex-direction: column; gap: 16px; }
.login-form .el-form-item { margin-bottom: 0; width: 100%; }

.footer-switch a {
  font-size: 13px;
  color: #909399;
  cursor: pointer;
}
.footer-switch a:hover { color: #409eff; }
.footer-switch a.active-link { color: #409eff; font-weight: 500; }
.switch-divider { color: #dcdfe6; font-size: 12px; margin: 0 4px; }

.input-wrap { width: 100%; }
.input-icon { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); font-size: 16px; color: #c0c4cc; z-index: 1; }
.custom-input { width: 100%; }
.custom-input :deep(.el-input__wrapper) { padding-left: 44px; padding-right: 40px; height: 44px; border-radius: 8px; box-shadow: 0 0 0 1px #dcdfe6 inset; }
.custom-input :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #409eff inset; }
.custom-input :deep(.el-input__inner) { font-size: 14px; }

.pwd-toggle { position: absolute; right: 6px; top: 50%; transform: translateY(-50%); z-index: 1; font-size: 16px; border: none; padding: 4px; color: #c0c4cc; }
.pwd-toggle:hover { background: transparent; color: #909399; }

/* 验证码 */
.captcha-row { display: flex; align-items: center; gap: 12px; }
.captcha-question {
  flex-shrink: 0;
  padding: 8px 16px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  letter-spacing: 2px;
  cursor: pointer;
  user-select: none;
  min-width: 90px;
  text-align: center;
}
.captcha-question:hover { border-color: #409eff; }
.captcha-input { flex: 1; }
.captcha-input :deep(.el-input__wrapper) { height: 44px; border-radius: 8px; }

/* 验证码 */
.code-row { display: flex; gap: 12px; width: 100%; }
.code-row .input-wrap { flex: 1; }
.code-btn { flex-shrink: 0; height: 44px; border-radius: 8px; }

.submit-btn { width: 100%; height: 44px; border-radius: 8px; font-size: 15px; font-weight: 500; margin-top: 4px; }
.submit-btn :deep(.el-loading-spinner) .path { stroke: #fff; }

.login-footer { display: flex; justify-content: space-between; align-items: center; margin-top: -4px; }
.forgot-link { font-size: 13px; color: #409eff; cursor: pointer; }
.forgot-link:hover { color: #66b1ff; }

.footer { text-align: center; margin-top: 20px; padding-top: 14px; border-top: 1px solid #f0f2f5; font-size: 12px; color: #c0c4cc; }
</style>
