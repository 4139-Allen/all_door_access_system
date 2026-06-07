<template>
  <view class="page">
    <view v-if="!logged" class="empty-state">
      <text class="empty-icon">&#128274;</text>
      <text class="empty-text">请先登录</text>
      <button class="btn-primary" @click="goLogin">去登录</button>
    </view>

    <view v-if="logged">
      <view class="stats-row">
        <view class="stat-card">
          <text class="stat-num">{{ stats.device_online || 0 }}</text>
          <text class="stat-label">在线设备</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ stats.device_offline || 0 }}</text>
          <text class="stat-label">离线设备</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ stats.today_log || 0 }}</text>
          <text class="stat-label">今日开门</text>
        </view>
      </view>

      <view class="section">
        <text class="section-title">快捷操作</text>
        <view class="quick-actions">
          <view class="action-item" @click="goDoors">
            <view class="action-icon">&#128682;</view>
            <text class="action-text">开门</text>
          </view>
          <view class="action-item" @click="goLogs">
            <view class="action-icon">&#128220;</view>
            <text class="action-text">记录</text>
          </view>
          <view v-if="canViewUsers" class="action-item" @click="goUsers">
            <view class="action-icon">&#128101;</view>
            <text class="action-text">用户管理</text>
          </view>
          <view v-if="canViewDevices" class="action-item" @click="goDevice">
            <view class="action-icon">&#128225;</view>
            <text class="action-text">设备管理</text>
          </view>
        </view>
      </view>

      <view class="section">
        <text class="section-title">最近开门记录</text>
        <view v-if="recentLogs.length == 0" class="empty-hint">
          <text class="text-muted">暂无记录</text>
        </view>
        <view v-if="recentLogs.length > 0" class="log-list">
          <view class="log-item" v-for="log in recentLogs" :key="log.id">
            <view class="log-left">
              <text class="log-device">{{ log.device_name }}</text>
              <text class="log-time">{{ formatTime(log.time) }}</text>
            </view>
            <text :class="['log-status', log.status == '成功' ? 'status-success' : 'status-danger']">
              {{ log.status }}
            </text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { isLoggedIn, hasPermission } from '../../stores/user'
import { getStatistics } from '../../api/stat'
import { getDoorLogs } from '../../api/door'

export default {
  data: function() {
    return {
      logged: false,
      canViewUsers: false,
      canViewDevices: false,
      stats: { device_online: 0, device_offline: 0, today_log: 0 },
      recentLogs: []
    }
  },
  onShow: function() {
    this.logged = isLoggedIn()
    this.canViewUsers = hasPermission('user.view') || hasPermission('user.manage')
    this.canViewDevices = hasPermission('device.view')
    if (this.logged) this.loadData()
  },
  methods: {
    goLogin: function() {
      uni.reLaunch({ url: '/pages/login/login' })
    },
    goDoors: function() {
      uni.switchTab({ url: '/pages/doors/doors' })
    },
    goLogs: function() {
      uni.switchTab({ url: '/pages/logs/logs' })
    },
    goUsers: function() {
      uni.navigateTo({ url: '/pages/users/users' })
    },
    goDevice: function() {
      uni.navigateTo({ url: '/pages/device/device' })
    },
    loadData: async function() {
      if (!this.logged) return
      try {
        var statRes = await getStatistics()
        this.stats = statRes.data
        if (hasPermission('door.view_own_log')) {
          var logRes = await getDoorLogs({ page: 1, size: 5 })
          this.recentLogs = logRes.data.list || []
        }
      } catch (e) {}
    },
    formatTime: function(t) {
      if (!t) return ''
      var d = new Date(t)
      return (d.getMonth() + 1) + '-' + d.getDate() + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0')
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

.stats-row {
  display: flex;
  gap: 20rpx;
  margin-bottom: 32rpx;
}

.stat-card {
  flex: 1;
  background: #ffffff;
  border-radius: 16rpx;
  padding: 28rpx 20rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
}

.stat-num {
  font-size: 44rpx;
  font-weight: 700;
  color: #6366f1;
}

.stat-label {
  font-size: 22rpx;
  color: #64748b;
  margin-top: 8rpx;
}

.section {
  margin-bottom: 32rpx;
}

.section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1e293b;
  display: block;
  margin-bottom: 20rpx;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 20rpx;
}

.action-item {
  width: calc(50% - 10rpx);
  background: #ffffff;
  border-radius: 16rpx;
  padding: 32rpx;
  display: flex;
  align-items: center;
  gap: 20rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
}

.action-icon {
  font-size: 44rpx;
}

.action-text {
  font-size: 28rpx;
  color: #1e293b;
  font-weight: 500;
}

.log-list {
  background: #ffffff;
  border-radius: 16rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
}

.log-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 28rpx;
  border-bottom: 1rpx solid #f1f5f9;
}

.log-item:last-child {
  border-bottom: none;
}

.log-left {
  display: flex;
  flex-direction: column;
}

.log-device {
  font-size: 28rpx;
  color: #1e293b;
}

.log-time {
  font-size: 22rpx;
  color: #94a3b8;
  margin-top: 6rpx;
}

.log-status {
  font-size: 24rpx;
  font-weight: 500;
}

.status-success {
  color: #22c55e;
}

.status-danger {
  color: #ef4444;
}

.empty-hint {
  text-align: center;
  padding: 40rpx;
}

.text-muted {
  color: #94a3b8;
  font-size: 26rpx;
}
</style>
