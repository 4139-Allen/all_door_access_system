import { reactive } from 'vue'

const deviceStatusMap = reactive({})

export function useDeviceStatus() {
  function updateDeviceStatus(deviceId, status) {
    deviceStatusMap[deviceId] = {
      status,
      lastSeen: Date.now()
    }
  }

  function getDeviceStatus(deviceId) {
    return deviceStatusMap[deviceId]?.status || 'offline'
  }

  function isDeviceOnline(deviceId) {
    return getDeviceStatus(deviceId) === 'online'
  }

  return {
    deviceStatusMap,
    updateDeviceStatus,
    getDeviceStatus,
    isDeviceOnline
  }
}
