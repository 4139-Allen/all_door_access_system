<template>
  <view class="page">
    <view v-if="!admin" class="empty-state">
      <text class="empty-icon">&#128274;</text>
      <text class="empty-text">无权限访问</text>
    </view>

    <view v-if="admin">
      <view class="search-bar">
        <input class="search-input" v-model="searchName" placeholder="搜索用户名" confirm-type="search" @confirm="handleSearch" />
        <button v-if="canManage" class="btn-add" @click="showCreateModal = true">+ 添加</button>
      </view>

      <view v-if="users.length == 0 && !loading" class="empty-hint">
        <text class="text-muted">暂无用户</text>
      </view>

      <view v-if="users.length > 0" class="user-list">
        <view class="user-item" v-for="user in users" :key="user.id">
          <view class="user-info">
            <text class="user-name">{{ user.username }}</text>
            <text class="user-role">{{ {admin: '超级管理员', operator: '操作员', user: '普通用户'}[user.role] || user.role }}</text>
            <text class="user-time">{{ formatTime(user.created_at) }}</text>
          </view>
          <view class="user-actions">
            <button class="btn-sm btn-view" @click="viewDevices(user)">设备</button>
            <button v-if="canManage && user.role != 'admin' && user.username != currentUsername" class="btn-sm btn-delete" @click="handleDelete(user)">删除</button>
          </view>
        </view>
      </view>

      <view v-if="users.length > 0 && users.length < total" class="load-more" @click="loadMore">
        <text class="load-more-text">加载更多</text>
      </view>

      <view class="modal-mask" v-if="showCreateModal" @click="showCreateModal = false">
        <view class="modal-content" @click.stop>
          <text class="modal-title">创建用户</text>
          <view class="form-item">
            <text class="label">用户名</text>
            <input class="input" v-model="newUsername" placeholder="字母、数字、下划线" maxlength="50" />
          </view>
          <view class="form-item">
            <text class="label">密码</text>
            <input class="input" v-model="newPassword" type="password" placeholder="至少6位" maxlength="72" />
          </view>
          <button class="btn-primary" :loading="createLoading" @click="handleCreate">创 建</button>
          <text class="cancel-link" @click="showCreateModal = false">取消</text>
        </view>
      </view>

      <view class="modal-mask" v-if="showDeviceModal" @click="closeDeviceModal">
        <view class="modal-content" @click.stop>
          <text class="modal-title">{{ selectedUser ? selectedUser.username : '' }} - 设备绑定</text>

          <!-- 已绑定设备 -->
          <view class="device-section">
            <text class="device-section-title">已绑定设备（{{ userDevices.length }}）</text>
            <view v-if="userDevices.length == 0" class="empty-hint">
              <text class="text-muted">暂无绑定设备</text>
            </view>
            <view v-if="userDevices.length > 0" class="device-mini-list">
              <view class="device-mini-item device-mini-row" v-for="d in userDevices" :key="d.id">
                <view class="device-mini-info">
                  <text class="device-mini-name">{{ d.name }}</text>
                  <text class="device-mini-loc">{{ d.location || '无位置' }}</text>
                </view>
                <button v-if="canBind" class="btn-sm btn-delete" :loading="unbindingDeviceId == d.id" @click="handleUnbind(d)">解绑</button>
              </view>
            </view>
          </view>

          <!-- 可绑定设备 -->
          <view v-if="canBind" class="device-section">
            <text class="device-section-title">可绑定设备（{{ bindableDevices.length }}）</text>
            <view v-if="bindableDevices.length == 0" class="empty-hint">
              <text class="text-muted">无可绑定设备</text>
            </view>
            <view v-if="bindableDevices.length > 0" class="device-mini-list">
              <view class="device-mini-item device-mini-row" v-for="d in bindableDevices" :key="d.id">
                <view class="device-mini-info">
                  <text class="device-mini-name">{{ d.name }}</text>
                  <text class="device-mini-loc">{{ d.location || '无位置' }}</text>
                </view>
                <button class="btn-sm btn-bind" :loading="bindingDeviceId == d.id" @click="handleBind(d)">绑定</button>
              </view>
            </view>
          </view>

          <text class="cancel-link" @click="closeDeviceModal">关闭</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { hasPermission } from '../../stores/user'
import { getUsers, createUser, deleteUser, getUserDevices } from '../../api/user'
import { getDevices, bindUserDevice, unbindUserDevice } from '../../api/device'

export default {
  data: function() {
    return {
      admin: false,
      canManage: false,
      currentUsername: '',
      users: [],
      total: 0,
      page: 1,
      loading: false,
      searchName: '',
      showCreateModal: false,
      newUsername: '',
      newPassword: '',
      createLoading: false,
      showDeviceModal: false,
      selectedUser: null,
      userDevices: [],
      allDevices: [],
      bindingDeviceId: null,
      unbindingDeviceId: null,
      canBind: false
    }
  },
  computed: {
    // 可绑定设备 = 全部设备中未被当前用户绑定的
    bindableDevices: function() {
      var boundIds = {}
      this.userDevices.forEach(function(d) { boundIds[d.id] = true })
      return this.allDevices.filter(function(d) { return !boundIds[d.id] })
    }
  },
  onShow: function() {
    this.admin = hasPermission('user.view') || hasPermission('user.manage')
    this.canManage = hasPermission('user.manage')
    this.canBind = hasPermission('device.bind')
    this.currentUsername = uni.getStorageSync('username') || ''
    if (this.admin) this.loadUsers(true)
  },
  methods: {
    loadUsers: async function(reset) {
      if (!this.admin) return
      if (reset) {
        this.page = 1
        this.users = []
      }
      this.loading = true
      try {
        var params = { page: this.page, size: 20 }
        if (this.searchName) params.username = this.searchName
        var res = await getUsers(params)
        if (reset) {
          this.users = res.data.list || []
        } else {
          this.users = this.users.concat(res.data.list || [])
        }
        this.total = res.data.total || 0
      } catch (e) {} finally {
        this.loading = false
      }
    },
    loadMore: function() {
      this.page++
      this.loadUsers(false)
    },
    handleSearch: function() {
      this.loadUsers(true)
    },
    handleCreate: async function() {
      if (!this.newUsername.trim()) {
        uni.showToast({ title: '请输入用户名', icon: 'none' })
        return
      }
      if (!this.newPassword || this.newPassword.length < 6) {
        uni.showToast({ title: '密码至少6位', icon: 'none' })
        return
      }
      this.createLoading = true
      try {
        await createUser({ username: this.newUsername.trim(), password: this.newPassword })
        uni.showToast({ title: '创建成功', icon: 'success' })
        this.showCreateModal = false
        this.newUsername = ''
        this.newPassword = ''
        this.loadUsers(true)
      } catch (e) {} finally {
        this.createLoading = false
      }
    },
    handleDelete: function(user) {
      var self = this
      uni.showModal({
        title: '确认删除',
        content: '确定删除用户「' + user.username + '」吗？',
        success: async function(res) {
          if (res.confirm) {
            try {
              await deleteUser(user.id)
              uni.showToast({ title: '删除成功', icon: 'success' })
              self.loadUsers(true)
            } catch (e) {}
          }
        }
      })
    },
    viewDevices: async function(user) {
      this.selectedUser = user
      this.showDeviceModal = true
      this.bindingDeviceId = null
      this.unbindingDeviceId = null
      try {
        var res = await getUserDevices(user.id)
        this.userDevices = res.data || []
      } catch (e) {
        this.userDevices = []
      }
      try {
        var dres = await getDevices({ page: 1, size: 9999 })
        this.allDevices = dres.data.list || []
      } catch (e) {
        this.allDevices = []
      }
    },
    closeDeviceModal: function() {
      this.showDeviceModal = false
      this.selectedUser = null
      this.userDevices = []
      this.allDevices = []
    },
    refreshDeviceData: async function() {
      try {
        var res = await getUserDevices(this.selectedUser.id)
        this.userDevices = res.data || []
      } catch (e) {
        this.userDevices = []
      }
    },
    handleBind: function(device) {
      var self = this
      uni.showModal({
        title: '确认绑定',
        content: '确定将设备「' + device.name + '」绑定给用户「' + this.selectedUser.username + '」吗？',
        success: async function(res) {
          if (res.confirm) {
            self.bindingDeviceId = device.id
            try {
              await bindUserDevice(device.id, self.selectedUser.id)
              uni.showToast({ title: '绑定成功', icon: 'success' })
              await self.refreshDeviceData()
            } catch (e) {} finally {
              self.bindingDeviceId = null
            }
          }
        }
      })
    },
    handleUnbind: function(device) {
      var self = this
      uni.showModal({
        title: '确认解绑',
        content: '确定解绑用户「' + this.selectedUser.username + '」与设备「' + device.name + '」的绑定关系吗？',
        success: async function(res) {
          if (res.confirm) {
            self.unbindingDeviceId = device.id
            try {
              await unbindUserDevice(device.id, self.selectedUser.id)
              uni.showToast({ title: '解绑成功', icon: 'success' })
              await self.refreshDeviceData()
            } catch (e) {} finally {
              self.unbindingDeviceId = null
            }
          }
        }
      })
    },
    formatTime: function(t) {
      if (!t) return ''
      var d = new Date(t)
      return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
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
}

.search-bar {
  display: flex;
  gap: 16rpx;
  margin-bottom: 24rpx;
}

.search-input {
  flex: 1;
  height: 72rpx;
  background: #ffffff;
  border: 2rpx solid #e2e8f0;
  border-radius: 12rpx;
  padding: 0 24rpx;
  font-size: 26rpx;
}

.btn-add {
  height: 72rpx;
  line-height: 72rpx;
  background: #6366f1;
  color: #ffffff;
  font-size: 26rpx;
  border-radius: 12rpx;
  border: none;
  padding: 0 24rpx;
}

.user-list {
  background: #ffffff;
  border-radius: 16rpx;
  overflow: hidden;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
}

.user-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 28rpx;
  border-bottom: 1rpx solid #f1f5f9;
}

.user-item:last-child {
  border-bottom: none;
}

.user-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.user-name {
  font-size: 28rpx;
  color: #1e293b;
  font-weight: 500;
}

.user-role {
  font-size: 22rpx;
  color: #64748b;
  margin-top: 4rpx;
}

.user-time {
  font-size: 22rpx;
  color: #94a3b8;
  margin-top: 4rpx;
}

.user-actions {
  display: flex;
  gap: 12rpx;
}

.btn-sm {
  height: 56rpx;
  line-height: 56rpx;
  font-size: 22rpx;
  border-radius: 8rpx;
  border: none;
  padding: 0 20rpx;
}

.btn-view {
  background: #e0e7ff;
  color: #6366f1;
}

.btn-delete {
  background: #fee2e2;
  color: #dc2626;
}

.load-more {
  text-align: center;
  padding: 32rpx;
}

.load-more-text {
  color: #6366f1;
  font-size: 26rpx;
}

.empty-hint {
  text-align: center;
  padding: 40rpx;
}

.text-muted {
  color: #94a3b8;
  font-size: 26rpx;
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

.btn-primary {
  width: 100%;
  height: 80rpx;
  line-height: 80rpx;
  background: #6366f1;
  color: #ffffff;
  font-size: 30rpx;
  border-radius: 12rpx;
  border: none;
}

.cancel-link {
  display: block;
  text-align: center;
  color: #94a3b8;
  font-size: 26rpx;
  margin-top: 24rpx;
}

.device-section {
  margin-bottom: 28rpx;
}

.device-section-title {
  font-size: 26rpx;
  color: #64748b;
  margin-bottom: 12rpx;
  display: block;
}

.device-mini-list {
  max-height: 320rpx;
  overflow-y: auto;
}

.device-mini-item {
  padding: 16rpx 0;
  border-bottom: 1rpx solid #f1f5f9;
}

.device-mini-item:last-child {
  border-bottom: none;
}

.device-mini-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.device-mini-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.device-mini-name {
  font-size: 28rpx;
  color: #1e293b;
  display: block;
}

.device-mini-loc {
  font-size: 22rpx;
  color: #94a3b8;
  margin-top: 4rpx;
  display: block;
}

.btn-bind {
  background: #e0e7ff;
  color: #6366f1;
}
</style>
