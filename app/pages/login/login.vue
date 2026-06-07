<template>
  <view class="login-page">
    <view class="logo-area">
      <view class="logo-icon">
        <view class="lock-shackle"></view>
        <view class="lock-body"></view>
      </view>
      <text class="app-name">智能门禁</text>
      <text class="app-desc">Smart Door Access</text>
    </view>

    <view class="form-card">
      <view class="form-item">
        <text class="label">用户名</text>
        <input class="input" v-model="username" placeholder="请输入用户名" maxlength="50" />
      </view>
      <view class="form-item">
        <text class="label">密码</text>
        <input class="input" v-model="password" type="password" placeholder="请输入密码" maxlength="72" />
      </view>
      <button class="btn-primary" :loading="loading" @click="handleLogin">登 录</button>
    </view>

    <view class="register-link">
      <text class="text-muted">还没有账号？</text>
      <text class="link" @click="showRegister = true">立即注册</text>
    </view>

    <view class="modal-mask" v-if="showRegister" @click="showRegister = false">
      <view class="modal-content" @click.stop>
        <text class="modal-title">注册账号</text>
        <view class="form-item">
          <text class="label">用户名</text>
          <input class="input" v-model="regUsername" placeholder="字母、数字、下划线" maxlength="50" />
        </view>
        <view class="form-item">
          <text class="label">密码</text>
          <input class="input" v-model="regPassword" type="password" placeholder="至少6位" maxlength="72" />
        </view>
        <view class="form-item">
          <text class="label">确认密码</text>
          <input class="input" v-model="regConfirm" type="password" placeholder="再次输入密码" maxlength="72" />
        </view>
        <button class="btn-primary" :loading="regLoading" @click="handleRegister">注 册</button>
        <text class="cancel-link" @click="showRegister = false">取消</text>
      </view>
    </view>
  </view>
</template>

<script>
import { login, register } from '../../api/auth'
import { isLoggedIn as checkHasToken, saveLoginInfo } from '../../stores/user'

export default {
  data: function() {
    return {
      username: '',
      password: '',
      loading: false,
      showRegister: false,
      regUsername: '',
      regPassword: '',
      regConfirm: '',
      regLoading: false
    }
  },
  onShow: function() {
    if (checkHasToken()) {
      uni.switchTab({ url: '/pages/index/index' })
    }
  },
  methods: {
    handleLogin: async function() {
      if (!this.username.trim()) {
        uni.showToast({ title: '请输入用户名', icon: 'none' })
        return
      }
      if (!this.password) {
        uni.showToast({ title: '请输入密码', icon: 'none' })
        return
      }
      this.loading = true
      try {
        var res = await login({ username: this.username.trim(), password: this.password })
        saveLoginInfo(res.data.token, res.data.role, this.username.trim(), res.data.permissions, res.data.role_name, res.data.user_id)
        uni.switchTab({ url: '/pages/index/index' })
      } catch (e) {
        // request.js already shows toast
      } finally {
        this.loading = false
      }
    },
    handleRegister: async function() {
      if (!this.regUsername.trim()) {
        uni.showToast({ title: '请输入用户名', icon: 'none' })
        return
      }
      if (!this.regPassword || this.regPassword.length < 6) {
        uni.showToast({ title: '密码至少6位', icon: 'none' })
        return
      }
      if (this.regPassword !== this.regConfirm) {
        uni.showToast({ title: '两次密码不一致', icon: 'none' })
        return
      }
      this.regLoading = true
      try {
        await register({ username: this.regUsername.trim(), password: this.regPassword })
        uni.showToast({ title: '注册成功，请登录', icon: 'success' })
        this.showRegister = false
        this.username = this.regUsername.trim()
        this.regUsername = ''
        this.regPassword = ''
        this.regConfirm = ''
      } catch (e) {
        // request.js already shows toast
      } finally {
        this.regLoading = false
      }
    }
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 48rpx 60rpx;
  background: linear-gradient(180deg, #1e293b 0%, #334155 50%, #f1f5f9 100%);
}

.logo-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 60rpx;
}

.logo-icon {
  width: 140rpx;
  height: 140rpx;
  background: #000000;
  border-radius: 32rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 20rpx;
}

.lock-shackle {
  width: 48rpx;
  height: 36rpx;
  border: 5rpx solid #ffffff;
  border-bottom: none;
  border-radius: 24rpx 24rpx 0 0;
}

.lock-body {
  width: 60rpx;
  height: 48rpx;
  background: #ffffff;
  border-radius: 10rpx;
  position: relative;
}

.lock-body::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 16rpx;
  height: 20rpx;
  background: #000000;
  border-radius: 0 0 8rpx 8rpx;
}

.app-name {
  font-size: 48rpx;
  font-weight: 700;
  color: #ffffff;
}

.app-desc {
  font-size: 24rpx;
  color: #94a3b8;
  margin-top: 8rpx;
}

.form-card {
  width: 100%;
  background: #ffffff;
  border-radius: 24rpx;
  padding: 48rpx 36rpx;
  box-shadow: 0 4rpx 24rpx rgba(0, 0, 0, 0.08);
}

.form-item {
  margin-bottom: 32rpx;
}

.label {
  font-size: 26rpx;
  color: #64748b;
  margin-bottom: 12rpx;
  display: block;
}

.input {
  width: 100%;
  height: 88rpx;
  border: 2rpx solid #e2e8f0;
  border-radius: 12rpx;
  padding: 0 24rpx;
  font-size: 30rpx;
  color: #1e293b;
}

.btn-primary {
  width: 100%;
  height: 88rpx;
  line-height: 88rpx;
  background: #6366f1;
  color: #ffffff;
  font-size: 32rpx;
  font-weight: 600;
  border-radius: 12rpx;
  border: none;
  margin-top: 16rpx;
}

.btn-primary:active {
  background: #4f46e5;
}

.register-link {
  margin-top: 32rpx;
  display: flex;
  align-items: center;
}

.text-muted {
  color: #94a3b8;
  font-size: 26rpx;
}

.link {
  color: #6366f1;
  font-size: 26rpx;
  margin-left: 8rpx;
}

.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.modal-content {
  width: 85%;
  background: #ffffff;
  border-radius: 24rpx;
  padding: 48rpx 36rpx;
}

.modal-title {
  font-size: 34rpx;
  font-weight: 600;
  color: #1e293b;
  display: block;
  text-align: center;
  margin-bottom: 36rpx;
}

.cancel-link {
  display: block;
  text-align: center;
  color: #94a3b8;
  font-size: 26rpx;
  margin-top: 24rpx;
}
</style>
