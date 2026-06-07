<template>
  <view class="page">
    <view v-if="!logged" class="empty-state">
      <text class="empty-icon">&#128274;</text>
      <text class="empty-text">请先登录</text>
      <button class="btn-primary" @click="goLogin">去登录</button>
    </view>

    <view v-if="logged">
      <view v-if="devices.length == 0 && !loading" class="empty-state">
        <text class="empty-icon">&#128225;</text>
        <text class="empty-text">暂无绑定设备</text>
      </view>

      <view v-if="devices.length > 0" class="device-list">
        <view class="device-card" v-for="device in devices" :key="device.id">
          <view class="device-header">
            <view class="device-info">
              <text class="device-name">{{ device.name }}</text>
              <text class="device-location">{{ device.location }}</text>
            </view>
            <view :class="['status-badge', device.status == 'online' ? 'online' : 'offline']">
              {{ device.status == 'online' ? '在线' : '离线' }}
            </view>
          </view>
          <button
            v-if="canOpen"
            class="btn-open"
            :class="{ 'btn-disabled': device.status != 'online' || openingId == device.id }"
            :disabled="device.status != 'online' || openingId == device.id"
            @click="handleOpen(device)"
          >
            {{ openingId == device.id ? '开门中...' : '开门' }}
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { isLoggedIn, hasPermission } from '../../stores/user'
import { getDevices } from '../../api/device'
import { openDoor } from '../../api/door'

export default {
  data: function() {
    return {
      logged: false,
      canOpen: false,
      devices: [],
      loading: false,
      openingId: null
    }
  },
  onShow: function() {
    this.logged = isLoggedIn()
    this.canOpen = hasPermission('door.open')
    if (this.logged) this.loadDevices()
  },
  methods: {
    goLogin: function() {
      uni.reLaunch({ url: '/pages/login/login' })
    },
    loadDevices: async function() {
      if (!this.logged) return
      this.loading = true
      try {
        var res = await getDevices({ page: 1, size: 50 })
        this.devices = res.data.list || []
      } catch (e) {} finally {
        this.loading = false
      }
    },
    handleOpen: function(device) {
      var self = this
      uni.showModal({
        title: '确认开门',
        content: '确定要打开「' + device.name + '」吗？',
        success: async function(res) {
          if (res.confirm) {
            self.openingId = device.id
            try {
              await openDoor(device.id)
              uni.showToast({ title: '开门成功', icon: 'success' })
              self.loadDevices()
            } catch (e) {} finally {
              self.openingId = null
            }
          }
        }
      })
    }
  },
  onPullDownRefresh: function() {
    var self = this
    this.loadDevices().finally(function() { uni.stopPullDownRefresh() })
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

.device-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.device-card {
  background: #ffffff;
  border-radius: 16rpx;
  padding: 28rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
}

.device-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24rpx;
}

.device-info {
  display: flex;
  flex-direction: column;
}

.device-name {
  font-size: 32rpx;
  font-weight: 600;
  color: #1e293b;
}

.device-location {
  font-size: 24rpx;
  color: #64748b;
  margin-top: 8rpx;
}

.status-badge {
  font-size: 22rpx;
  padding: 6rpx 16rpx;
  border-radius: 20rpx;
  font-weight: 500;
}

.status-badge.online {
  background: #dcfce7;
  color: #16a34a;
}

.status-badge.offline {
  background: #fee2e2;
  color: #dc2626;
}

.btn-open {
  width: 100%;
  height: 80rpx;
  line-height: 80rpx;
  background: #6366f1;
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
  border-radius: 12rpx;
  border: none;
}

.btn-open:active {
  background: #4f46e5;
}

.btn-disabled {
  background: #94a3b8 !important;
}
</style>
