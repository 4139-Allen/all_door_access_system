<template>
  <view class="page">
    <view v-if="!logged" class="empty-state">
      <text class="empty-icon">&#128274;</text>
      <text class="empty-text">请先登录</text>
      <button class="btn-primary" @click="goLogin">去登录</button>
    </view>

    <view v-if="logged">
      <view class="profile-card">
        <view class="avatar">{{ displayName.charAt(0).toUpperCase() }}</view>
        <view class="user-info">
          <text class="username">{{ displayName }}</text>
          <text class="role">{{ roleLabel }}</text>
        </view>
      </view>

      <view class="menu-list">
        <view class="menu-item" @click="showPasswordModal = true">
          <text class="menu-icon">&#128273;</text>
          <text class="menu-text">修改密码</text>
          <text class="menu-arrow">&#9656;</text>
        </view>
        <view class="menu-item danger" @click="handleLogout">
          <text class="menu-icon">&#9211;</text>
          <text class="menu-text">退出登录</text>
          <text class="menu-arrow">&#9656;</text>
        </view>
      </view>

      <view class="modal-mask" v-if="showPasswordModal" @click="showPasswordModal = false">
        <view class="modal-content" @click.stop>
          <text class="modal-title">修改密码</text>
          <view class="form-item">
            <text class="label">旧密码</text>
            <input class="input" v-model="oldPassword" type="password" placeholder="请输入旧密码" />
          </view>
          <view class="form-item">
            <text class="label">新密码</text>
            <input class="input" v-model="newPassword" type="password" placeholder="至少6位" />
          </view>
          <view class="form-item">
            <text class="label">确认新密码</text>
            <input class="input" v-model="confirmPassword" type="password" placeholder="再次输入新密码" />
          </view>
          <button class="btn-primary" :loading="pwdLoading" @click="handleChangePassword">确认修改</button>
          <text class="cancel-link" @click="showPasswordModal = false">取消</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { isLoggedIn, isAdmin, getUsername, getRole, clearLoginInfo } from '../../stores/user'
import { changePassword, logout } from '../../api/auth'

const ROLE_LABEL_MAP = { admin: '超级管理员', operator: '操作员', user: '普通用户' }

export default {
  data: function() {
    return {
      logged: false,
      admin: false,
      displayName: '',
      roleLabel: '',
      showPasswordModal: false,
      oldPassword: '',
      newPassword: '',
      confirmPassword: '',
      pwdLoading: false
    }
  },
  onShow: function() {
    this.logged = isLoggedIn()
    this.admin = isAdmin()
    this.displayName = getUsername()
    this.roleLabel = ROLE_LABEL_MAP[getRole()] || getRole() || '普通用户'
  },
  methods: {
    goLogin: function() {
      uni.reLaunch({ url: '/pages/login/login' })
    },
    handleChangePassword: async function() {
      if (!this.oldPassword || !this.newPassword || !this.confirmPassword) {
        uni.showToast({ title: '请填写所有字段', icon: 'none' })
        return
      }
      if (this.newPassword.length < 6) {
        uni.showToast({ title: '新密码至少6位', icon: 'none' })
        return
      }
      if (this.newPassword !== this.confirmPassword) {
        uni.showToast({ title: '两次密码不一致', icon: 'none' })
        return
      }
      this.pwdLoading = true
      try {
        await changePassword({ old_password: this.oldPassword, new_password: this.newPassword })
        uni.showToast({ title: '密码修改成功', icon: 'success' })
        this.showPasswordModal = false
        this.oldPassword = ''
        this.newPassword = ''
        this.confirmPassword = ''
        this.handleLogout()
      } catch (e) {} finally {
        this.pwdLoading = false
      }
    },
    handleLogout: function() {
      var self = this
      uni.showModal({
        title: '提示',
        content: '确定退出登录吗？',
        success: async function(res) {
          if (res.confirm) {
            try { await logout() } catch (e) {}
            clearLoginInfo()
            uni.reLaunch({ url: '/pages/login/login' })
          }
        }
      })
    }
  }
}
</script>

<style scoped>
.page {
  padding: 24rpx 32rpx;
  min-height: 100vh;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.empty-icon {
  font-size: 80rpx;
  margin-bottom: 20rpx;
}

.empty-text {
  font-size: 30rpx;
  color: #64748b;
  margin-bottom: 32rpx;
}

.btn-primary {
  width: 300rpx;
  height: 80rpx;
  line-height: 80rpx;
  background: #6366f1;
  color: #ffffff;
  font-size: 30rpx;
  border-radius: 12rpx;
  border: none;
}

.profile-card {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border-radius: 20rpx;
  padding: 40rpx 32rpx;
  display: flex;
  align-items: center;
  gap: 28rpx;
  margin-bottom: 32rpx;
}

.avatar {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44rpx;
  font-weight: 700;
  color: #ffffff;
}

.user-info {
  display: flex;
  flex-direction: column;
}

.username {
  font-size: 34rpx;
  font-weight: 600;
  color: #ffffff;
}

.role {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 8rpx;
}

.menu-list {
  background: #ffffff;
  border-radius: 16rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 32rpx 28rpx;
  border-bottom: 1rpx solid #f1f5f9;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-item.danger .menu-text {
  color: #ef4444;
}

.menu-icon {
  font-size: 36rpx;
  margin-right: 20rpx;
}

.menu-text {
  flex: 1;
  font-size: 30rpx;
  color: #1e293b;
}

.menu-arrow {
  font-size: 28rpx;
  color: #94a3b8;
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

.form-item {
  margin-bottom: 24rpx;
}

.label {
  font-size: 26rpx;
  color: #64748b;
  margin-bottom: 12rpx;
  display: block;
}

.input {
  width: 100%;
  height: 80rpx;
  border: 2rpx solid #e2e8f0;
  border-radius: 12rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
}

.cancel-link {
  display: block;
  text-align: center;
  color: #94a3b8;
  font-size: 26rpx;
  margin-top: 24rpx;
}
</style>
