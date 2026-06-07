<template>
  <view class="page">
    <view v-if="!admin" class="empty-state">
      <text class="empty-icon">&#128274;</text>
      <text class="empty-text">无权限访问</text>
    </view>

    <view v-if="admin">
      <view class="search-bar">
        <input class="search-input" v-model="searchName" placeholder="搜索设备名称" confirm-type="search" @confirm="handleSearch" />
        <button v-if="canCreate" class="btn-add" @click="openCreateModal">+ 添加</button>
      </view>

      <view v-if="devices.length == 0 && !loading" class="empty-hint">
        <text class="text-muted">暂无设备</text>
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
          <view class="device-actions">
            <button v-if="canEdit" class="btn-sm btn-edit" @click="openEditModal(device)">编辑</button>
            <button v-if="canDelete" class="btn-sm btn-delete" @click="handleDelete(device)">删除</button>
          </view>
        </view>
      </view>

      <view v-if="devices.length > 0 && devices.length < total" class="load-more" @click="loadMore">
        <text class="load-more-text">加载更多</text>
      </view>

      <view class="modal-mask" v-if="showModal" @click="showModal = false">
        <view class="modal-content" @click.stop>
          <text class="modal-title">{{ editingDevice ? '编辑设备' : '创建设备' }}</text>
          <view class="form-item">
            <text class="label">设备名称</text>
            <input class="input" v-model="formName" placeholder="如 001" maxlength="100" />
          </view>
          <view class="form-item">
            <text class="label">位置</text>
            <input class="input" v-model="formLocation" placeholder="如 大门入口" maxlength="200" />
          </view>
          <button class="btn-primary" :loading="submitLoading" @click="handleSubmit">确 认</button>
          <text class="cancel-link" @click="showModal = false">取消</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { hasPermission } from '../../stores/user'
import { getDevices, createDevice, updateDevice, deleteDevice } from '../../api/device'

export default {
  data: function() {
    return {
      admin: false,
      canCreate: false,
      canEdit: false,
      canDelete: false,
      devices: [],
      total: 0,
      page: 1,
      loading: false,
      searchName: '',
      showModal: false,
      editingDevice: null,
      formName: '',
      formLocation: '',
      submitLoading: false
    }
  },
  onShow: function() {
    this.admin = hasPermission('device.view')
    this.canCreate = hasPermission('device.create')
    this.canEdit = hasPermission('device.edit')
    this.canDelete = hasPermission('device.delete')
    if (this.admin) this.loadDevices(true)
  },
  methods: {
    loadDevices: async function(reset) {
      if (!this.admin) return
      if (reset) {
        this.page = 1
        this.devices = []
      }
      this.loading = true
      try {
        var params = { page: this.page, size: 20 }
        if (this.searchName) params.name = this.searchName
        var res = await getDevices(params)
        if (reset) {
          this.devices = res.data.list || []
        } else {
          this.devices = this.devices.concat(res.data.list || [])
        }
        this.total = res.data.total || 0
      } catch (e) {} finally {
        this.loading = false
      }
    },
    loadMore: function() {
      this.page++
      this.loadDevices(false)
    },
    handleSearch: function() {
      this.loadDevices(true)
    },
    openCreateModal: function() {
      this.editingDevice = null
      this.formName = ''
      this.formLocation = ''
      this.showModal = true
    },
    openEditModal: function(device) {
      this.editingDevice = device
      this.formName = device.name
      this.formLocation = device.location
      this.showModal = true
    },
    handleSubmit: async function() {
      if (!this.formName.trim()) {
        uni.showToast({ title: '请输入设备名称', icon: 'none' })
        return
      }
      if (!this.formLocation.trim()) {
        uni.showToast({ title: '请输入位置', icon: 'none' })
        return
      }
      this.submitLoading = true
      try {
        if (this.editingDevice) {
          await updateDevice(this.editingDevice.id, { name: this.formName.trim(), location: this.formLocation.trim() })
          uni.showToast({ title: '更新成功', icon: 'success' })
        } else {
          await createDevice({ name: this.formName.trim(), location: this.formLocation.trim() })
          uni.showToast({ title: '创建成功', icon: 'success' })
        }
        this.showModal = false
        this.loadDevices(true)
      } catch (e) {} finally {
        this.submitLoading = false
      }
    },
    handleDelete: function(device) {
      var self = this
      uni.showModal({
        title: '确认删除',
        content: '确定删除设备「' + device.name + '」吗？需先解绑所有用户。',
        success: async function(res) {
          if (res.confirm) {
            try {
              await deleteDevice(device.id)
              uni.showToast({ title: '删除成功', icon: 'success' })
              self.loadDevices(true)
            } catch (e) {}
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
  margin-bottom: 20rpx;
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

.device-actions {
  display: flex;
  gap: 16rpx;
}

.btn-sm {
  flex: 1;
  height: 64rpx;
  line-height: 64rpx;
  font-size: 26rpx;
  border-radius: 10rpx;
  border: none;
}

.btn-edit {
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
</style>
