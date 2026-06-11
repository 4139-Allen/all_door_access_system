import { reactive, ref } from 'vue'
import { useRelativeTime } from '@/utils/formatTime'

const MAX_EVENTS = 50

const eventList = reactive([])
const deviceStatusMap = reactive({})
const alertList = reactive([])

export function useDoorEventStream() {
  function addDoorEvent(event) {
    eventList.unshift({
      id: Date.now() + Math.random(),
      username: event.username,
      device_name: event.device_name,
      location: event.location || '',
      action: event.action || '远程开门',
      status: event.status || '成功',
      timestamp: event.timestamp
    })
    if (eventList.length > MAX_EVENTS) {
      eventList.splice(MAX_EVENTS)
    }
  }

  function updateDeviceStatus(deviceId, status, deviceName, location) {
    deviceStatusMap[deviceId] = {
      status,
      device_name: deviceName,
      location: location || '',
      timestamp: new Date().toLocaleString()
    }
  }

  function addAlertEvent(event) {
    alertList.unshift({
      id: Date.now() + Math.random(),
      device_id: event.device_id,
      device_name: event.device_name,
      alert_type: event.alert_type,
      message: event.message,
      timestamp: event.timestamp
    })
    if (alertList.length > MAX_EVENTS) {
      alertList.splice(MAX_EVENTS)
    }
  }

  function getRelativeTime(timestamp) {
    return useRelativeTime(timestamp)
  }

  return {
    eventList,
    deviceStatusMap,
    alertList,
    addDoorEvent,
    updateDeviceStatus,
    addAlertEvent,
    getRelativeTime
  }
}
