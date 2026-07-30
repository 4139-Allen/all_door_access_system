"""
MQTT 服务层
负责与 MQTT Broker 通信，向硬件设备发布开门命令，订阅设备状态
"""
import asyncio
from asyncio import Future
import uuid
import time
from typing import Optional, Dict
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
from services.device_service import invalidate_all_device_cache
from services.stat_service import invalidate_all_stat_cache
from utils.service_exception_handler import service_exception_handler
from utils.logger import AppLogger

logger = AppLogger.get_logger()


# ==========================================
# 本地开门日志（密码/指纹/刷卡）
# ==========================================
@service_exception_handler
def _save_local_door_log(db: Session, device_id: str, action: str, status: str = "成功"):
    """记录本地开门日志并推送 WebSocket 通知（由 @service_exception_handler 统一处理异常）"""
    device = db.query(Device).filter(Device.name == device_id).first()
    if not device:
        return
    db.add(DoorLog(
        device_name=device.name,
        user_name="本地",
        action=action, status=status, time=datetime.now()
    ))
    db.commit()

    # 清除日志缓存和异常事件缓存
    from services.log_service import invalidate_log_cache
    from services.alert_service import invalidate_alert_cache
    invalidate_log_cache()
    invalidate_alert_cache()

    # 成功和失败都推送 WebSocket 通知
    if status == "成功":
        logger.info(f"本地开门记录 [{device_id}]: {action}")
    else:
        logger.warning(f"开门失败 [{device_id}]: {action} - {status}")

    mqtt_manager._schedule_send_door_event(device.id, "本地", device.name, device.location or "", action, status)


class MQTTManager:
    """MQTT 连接管理器，单例模式"""

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._last_disconnect_log: float = 0  # 上次断线日志时间
        self._last_connect_log: float = 0     # 上次连接成功日志时间
        self._retry_count: int = 0            # 连续断线次数（超过10次日志降频）
        # 客户端唯一标识，避免 Mosquitto 因重复 ID 踢掉旧连接
        self._client_id = f"door-backend-{uuid.uuid4().hex[:8]}"
        # 开门确认：device_name -> Future，等待设备回复 OPENED
        self._pending_open: Dict[str, Future] = {}

    def start(self):
        """初始化并连接 MQTT Broker"""
        # 在启动时获取事件循环引用（主线程运行的循环）
        self._loop = asyncio.get_event_loop()
        try:
            self.client = mqtt.Client(client_id=self._client_id, clean_session=True)
            if MQTT_USERNAME:
                self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

            # 启用自动重连（指数退避：1秒 ~ 30秒）
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)

            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            self.client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)#60 秒心跳
            self.client.loop_start()
            logger.info(f"MQTT 客户端已启动，正在连接 {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        except Exception as e:
            logger.warning(f"MQTT 连接失败，设备控制功能不可用: {e}")
            self.client = None

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self._retry_count = 0

            # 限流：30 秒内只打一次连接日志，避免频繁重连时刷屏
            now = time.time()
            if now - self._last_connect_log > 30:
                self._last_connect_log = now
                logger.info(f"MQTT 已连接，已订阅 {MQTT_TOPIC_PREFIX}/+/status 和 {MQTT_TOPIC_PREFIX}/+/rssi")
            # 订阅（即使不打日志也要订阅，保证功能正常）
            client.subscribe(f"{MQTT_TOPIC_PREFIX}/+/status", qos=1)
            client.subscribe(f"{MQTT_TOPIC_PREFIX}/+/rssi", qos=0)
        else:
            logger.error(f"MQTT 连接失败，返回码: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            self._retry_count += 1
            # 连续断线超过 50 次 → 彻底停止（防止无限重连）
            if self._retry_count > 50:
                logger.warning(f"MQTT 连续 {self._retry_count} 次重连失败，已停止重连")
                client.loop_stop()
                client.disconnect()
                return
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

        # 更新在线状态到 Redis
        if redis_client and payload in ("ONLINE", "OK", "OPENED"):
            redis_client.setex(f"device:online:{device_id}", 70, "online")

            # 设备回复 OPENED → 通知等待的开门请求
            if payload == "OPENED":
                self._signal_open_confirmation(device_id)

            # 检查是否首次上线（不在已知在线列表中），避免心跳重复推送
            is_first_online = not is_device_known_online(device_id)

            # 推送设备在线状态到前端 + 注册到监控
            db = SessionLocal()
            try:
                device = db.query(Device).filter(Device.name == device_id).first()
                if device:
                    # 只有状态变化时才写数据库，避免每次心跳都 commit
                    if is_first_online or device.status != "online":
                        device.status = "online"
                        device.last_online_at = datetime.now()
                        db.commit()
                        invalidate_all_device_cache()
                        invalidate_all_stat_cache()
                        logger.info(f"设备状态变更 [online] [{device_id}]")

                    mark_device_online(device.id, device_id)

                    # 首次上线：检查锁定状态发 UNLOCK + 推 WebSocket 通知
                    if is_first_online:
                        lock_key = f"door:err:lock:{device_id}"
                        if not redis_client.exists(lock_key):
                            self.publish_command(device_id, "UNLOCK")
                        self._schedule_send_device_status(
                            device_id=device.id,
                            device_name=device.name,
                            status="online",
                            location=device.location or ""
                        )
            finally:
                db.close()

        # 记录本地开门日志（成功 + 失败）
        action_map = {
            # 成功事件
            "PWD_OK": ("密码开门", "成功"),
            "FP_OK": ("指纹开门", "成功"),
            "CARD_OK": ("刷卡开门", "成功"),
            # 失败事件
            "PWD_ERR": ("密码开门", "失败：密码错误"),
            "FP_ERR": ("指纹开门", "失败：指纹不匹配"),
            "CARD_ERR": ("刷卡开门", "失败：未授权卡片"),
        }
        if payload in action_map:
            action, status = action_map[payload]

            # 验证错误次数限制检查（密码/指纹/刷卡共用）
            if payload in ("PWD_ERR", "FP_ERR", "CARD_ERR") and redis_client:
                lock_key = f"door:err:lock:{device_id}"
                fail_key = f"door:err:fail:{device_id}"

                # 检查设备是否已被锁定
                if redis_client.exists(lock_key):
                    lock_ttl = redis_client.ttl(lock_key)
                    status = f"失败：设备已锁定（剩余{lock_ttl}秒）"
                    logger.warning(f"设备锁定中 [{device_id}]: 剩余{lock_ttl}秒")
                else:
                    # 增加失败计数
                    fail_count = redis_client.incr(fail_key)
                    # 首次失败设置过期时间（5分钟内统计）
                    if fail_count == 1:
                        redis_client.expire(fail_key, 300)

                    # 检查是否达到锁定阈值（5次）
                    if fail_count >= 5:
                        # 锁定设备5分钟
                        redis_client.setex(lock_key, 300, "locked")
                        # 删除失败计数
                        redis_client.delete(fail_key)
                        # 发送锁定命令给STM32
                        self.publish_command(device_id, "LOCK")
                        status = "失败：验证错误次数过多，设备锁定5分钟"
                        logger.warning(f"设备锁定 [{device_id}]: 5次错误，锁定5分钟")

            # 验证成功时重置失败计数
            if payload in ("PWD_OK", "FP_OK", "CARD_OK") and redis_client:
                fail_key = f"door:err:fail:{device_id}"
                redis_client.delete(fail_key)

            db = SessionLocal()
            try:
                _save_local_door_log(db, device_id, action, status)

                # 设备锁定时推送异常告警
                if "锁定" in status:
                    device = db.query(Device).filter(Device.name == device_id).first()
                    if device:
                        self._schedule_send_alert_event(
                            device_id=device.id,
                            device_name=device.name,
                            alert_type="lock",
                            message="验证错误次数过多，设备已锁定5分钟"
                        )
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

    def register_open_confirmation(self, device_name: str) -> Future:
        """注册一个 Future，等待设备回复 OPENED 确认开门"""
        future = self._loop.create_future()
        self._pending_open[device_name] = future
        return future

    def _signal_open_confirmation(self, device_name: str):
        """设备回复了 OPENED，通知等待的开门请求"""
        future = self._pending_open.pop(device_name, None)
        if future and not future.done():
            self._schedule_coroutine(
                self._do_set_future(future, True),
                f"发送开门确认通知 [{device_name}]"
            )

    async def _do_set_future(self, future: Future, value):
        """在事件循环线程中设置 Future 结果（线程安全）"""
        future.set_result(value)

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

    def _schedule_send_door_event(self, device_id: int, username: str, device_name: str, location: str, action: str, status: str = "成功"):
        self._schedule_coroutine(ws_manager.send_door_event(device_id, username, device_name, location, action, status), "发送开门事件")

    def _schedule_send_alert_event(self, device_id: int, device_name: str, alert_type: str, message: str):
        self._schedule_coroutine(ws_manager.send_alert_event(device_id, device_name, alert_type, message), "发送异常告警")

    def stop(self):
        """断开 MQTT 连接"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("MQTT 客户端已关闭")


# 全局单例
mqtt_manager = MQTTManager()
