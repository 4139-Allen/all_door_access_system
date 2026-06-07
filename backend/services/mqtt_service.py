"""
MQTT 服务层
负责与 MQTT Broker 通信，向硬件设备发布开门命令，订阅设备状态
"""
import asyncio
import time
from typing import Optional
from datetime import datetime

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from core.config import (
    MQTT_BROKER_HOST, MQTT_BROKER_PORT,
    MQTT_USERNAME, MQTT_PASSWORD, MQTT_TOPIC_PREFIX
)
from database.redis import redis_client
from database.db import SessionLocal
from database.models.device import Device
from database.models.door_log import DoorLog
from services.websocket_service import manager as ws_manager
from services.device_monitor_service import mark_device_online, is_device_known_online
from utils.service_exception_handler import service_exception_handler
from utils.logger import AppLogger

logger = AppLogger.get_logger()


# ==========================================
# 本地开门日志（密码/指纹/刷卡）
# ==========================================
@service_exception_handler
def _save_local_door_log(db: Session, device_id: str, action: str):
    """记录本地开门日志并推送 WebSocket 通知（由 @service_exception_handler 统一处理异常）"""
    device = db.query(Device).filter(Device.name == device_id).first()
    if not device:
        return
    db.add(DoorLog(
        user_id=None, device_id=device.id,
        action=action, status="成功", time=datetime.now()
    ))
    db.commit()
    logger.info(f"本地开门记录 [{device_id}]: {action}")
    mqtt_manager._schedule_send_door_event(device.id, "本地", device.name, device.location or "", action)


class MQTTManager:
    """MQTT 连接管理器，单例模式"""

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._last_disconnect_log: float = 0  # 上次断线日志时间

    def start(self):
        """初始化并连接 MQTT Broker"""
        # 在启动时获取事件循环引用（主线程运行的循环）
        self._loop = asyncio.get_event_loop()
        try:
            self.client = mqtt.Client(client_id="door-backend", clean_session=True)
            if MQTT_USERNAME:
                self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

            # 启用自动重连（指数退避：1秒 ~ 30秒）
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)

            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            self.client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            self.client.loop_start()
            logger.info(f"MQTT 客户端已启动，正在连接 {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        except Exception as e:
            logger.warning(f"MQTT 连接失败，设备控制功能不可用: {e}")
            self.client = None

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            # 订阅所有设备的状态上报和信号强度
            client.subscribe(f"{MQTT_TOPIC_PREFIX}/+/status", qos=1)
            client.subscribe(f"{MQTT_TOPIC_PREFIX}/+/rssi", qos=0)
            logger.info(f"MQTT 已连接，已订阅 {MQTT_TOPIC_PREFIX}/+/status 和 {MQTT_TOPIC_PREFIX}/+/rssi")
        else:
            logger.error(f"MQTT 连接失败，返回码: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            now = time.time()
            if now - self._last_disconnect_log > 30:
                self._last_disconnect_log = now
                logger.warning(f"MQTT 意外断开 (rc={rc})，将在后台自动重连...")

    def _on_message(self, client, userdata, msg):
        """处理设备上报的消息"""
        parts = msg.topic.split("/")
        if len(parts) != 3:
            return

        device_id = parts[1]
        msg_type = parts[2]
        payload = msg.payload.decode().strip()

        # 处理信号强度上报
        if msg_type == "rssi":
            try:
                rssi = int(payload)
                db = SessionLocal()
                try:
                    device = db.query(Device).filter(Device.name == device_id).first()
                    if device:
                        device.signal_strength = rssi
                        db.commit()
                        logger.info(f"设备信号强度 [{device_id}]: {rssi}dBm")
                finally:
                    db.close()
            except ValueError:
                logger.warning(f"无效的 RSSI 值 [{device_id}]: {payload}")
            return

        if msg_type != "status":
            return

        logger.info(f"MQTT 设备状态上报 [{device_id}]: {payload}")

        # 更新在线状态到 Redis
        if redis_client and payload in ("ONLINE", "OK", "OPENED"):
            redis_client.setex(f"device:online:{device_id}", 70, "online")

            # 检查是否首次上线（不在已知在线列表中），避免心跳重复推送
            is_first_online = not is_device_known_online(device_id)

            # 推送设备在线状态到前端 + 注册到监控
            db = SessionLocal()
            try:
                device = db.query(Device).filter(Device.name == device_id).first()
                if device:
                    device.status = "online"
                    device.last_online_at = datetime.now()
                    db.commit()
                    mark_device_online(device.id, device_id)
                    # 只有首次上线才推送 WebSocket 通知
                    if is_first_online:
                        self._schedule_send_device_status(
                            device_id=device.id,
                            device_name=device.name,
                            status="online",
                            location=device.location or ""
                        )
            finally:
                db.close()

        # 记录本地开门日志
        action_map = {"PWD_OK": "密码开门", "FP_OK": "指纹开门", "CARD_OK": "刷卡开门"}
        if payload in action_map:
            db = SessionLocal()
            try:
                _save_local_door_log(db, device_id, action_map[payload])
            finally:
                db.close()

    def publish_command(self, device_name: str, command: str):
        """
        向设备发布命令

        Args:
            device_name: 设备编号（如 "001"）
            command: 命令内容（如 "OPEN_DOOR"）
        """
        if not self.client or not self.connected:
            logger.warning(f"MQTT 未连接，无法发送命令到设备 {device_name}")
            return False

        topic = f"{MQTT_TOPIC_PREFIX}/{device_name}/command"
        result = self.client.publish(topic, command, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"MQTT 命令已发送 [{topic}] -> {command}")
            return True
        else:
            logger.error(f"MQTT 命令发送失败 [{topic}], rc={result.rc}")
            return False

    def _schedule_coroutine(self, coro, error_msg: str = "调度异步任务失败"):
        """统一调度异步协程（线程安全）"""
        if not self._loop or not self._loop.is_running():
            logger.warning(f"事件循环未运行，无法{error_msg}")
            return
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except Exception as e:
            logger.warning(f"{error_msg}: {e}")

    def _schedule_send_device_status(self, **kwargs):
        self._schedule_coroutine(ws_manager.send_device_status(**kwargs), "发送设备状态消息")

    def _schedule_send_door_event(self, device_id: int, username: str, device_name: str, location: str, action: str):
        self._schedule_coroutine(ws_manager.send_door_event(device_id, username, device_name, location, action), "发送开门事件")

    def stop(self):
        """断开 MQTT 连接"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("MQTT 客户端已关闭")


# 全局单例
mqtt_manager = MQTTManager()
