from database.models.device import Device
from database.models.user import User
from database.models.door_log import DoorLog
from datetime import datetime
from sqlalchemy.orm import Session
from services.device_service import check_user_permission
from services.mqtt_service import mqtt_manager
from services.stat_service import invalidate_stat_cache
from services.permission_service import user_has_permission
from services.log_service import invalidate_log_cache
from utils.service_exception_handler import service_exception_handler
from utils.logger import AppLogger
from core.exceptions import NotFoundError
from database.redis import redis_client
from services.alert_service import invalidate_alert_cache
import asyncio
import uuid

logger = AppLogger.get_logger()

# 远程开门冷却时间（秒）
DOOR_OPEN_COOLDOWN = 3


def _add_door_log(db: Session, device_name: str, user_name: str, status: str, ip: str = None):
    """快速创建开门日志并提交（存储设备名/用户名快照）"""
    db.add(DoorLog(
        device_name=device_name,
        user_name=user_name,
        action="远程开门",
        status=status,
        ip=ip,
        time=datetime.now()
    ))
    db.commit()

    # 清除日志缓存和异常事件缓存
    invalidate_log_cache()
    invalidate_alert_cache()


# ==========================================
# 1. 开门核心逻辑
# ==========================================
@service_exception_handler
async def open_door_service(db: Session, user_id: int, device_id: int, ip: str = None) -> dict:
    """
    开门核心逻辑（含缓存失效 + MQTT 命令发送）

    返回:
        dict: {"success", "message", "device_id", "username", "device_name", "location"}
    """
    # 1. 查询用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("用户不存在")

    # 2. 查询设备
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        logger.warning(f"开门失败 | 设备ID: {device_id} | 原因: 设备不存在")
        raise NotFoundError("设备不存在")

    username = user.username
    device_name = device.name

    # 3. 设备状态检查
    if device.status != "online":
        _add_door_log(db, device_name, username, "失败：设备不在线", ip)
        logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 设备不在线")
        raise PermissionError(f"设备「{device_name}」不在线，无法开门")

    # 3.1 Redis 实时在线检查（弥补 MySQL 状态更新延迟）
    if redis_client and not redis_client.exists(f"device:online:{device.name}"):
        _add_door_log(db, device_name, username, "失败：设备已断线", ip)
        logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: Redis 检测到设备离线")
        raise PermissionError(f"设备「{device_name}」已断线，无法开门")

    # 3.2 设备锁定检查（密码/指纹/刷卡错误5次后锁定）
    err_lock_key = f"door:err:lock:{device.name}"
    if redis_client and redis_client.exists(err_lock_key):
        lock_ttl = redis_client.ttl(err_lock_key)
        _add_door_log(db, device_name, username, f"失败：设备已锁定（剩余{lock_ttl}秒）", ip)
        logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 设备已锁定（剩余{lock_ttl}秒）")
        raise ValueError(f"设备已锁定，请 {lock_ttl} 秒后再试")

    # 4. 权限判断（有 device.view 权限可操作任意设备，否则需绑定）
    if not user_has_permission(db, user, "device.view"):
        if not check_user_permission(db, user_id, device_id):
            _add_door_log(db, device_name, username, "失败：无权限，未绑定该设备", ip)
            logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 无权限")
            raise PermissionError("无权限操作：你未绑定该设备，无法开门")

    # ===== 分布式锁（设备级互斥，防止多人同时操作同一门禁） =====
    lock_key = f"door:lock:{device_id}"
    lock_value = str(uuid.uuid4())
    if redis_client:
        locked = redis_client.set(lock_key, lock_value, ex=5, nx=True)
        if not locked:
            _add_door_log(db, device_name, username, "失败：设备正在被操作", ip)
            logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 设备忙")
            raise PermissionError("该设备正在操作中，请稍后")

    try:
        # 5. 冷却时间检查（防止频繁开门）
        cooldown_key = f"door:cooldown:{user_id}:{device_id}"
        if redis_client:
            if redis_client.exists(cooldown_key):
                _add_door_log(db, device_name, username, "失败：操作过于频繁", ip)
                logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 操作过于频繁")
                raise PermissionError(f"操作过于频繁，请 {DOOR_OPEN_COOLDOWN} 秒后再试")
            # 设置冷却时间
            redis_client.setex(cooldown_key, DOOR_OPEN_COOLDOWN, "1")

        # 6. 注册开门确认 + 发送 MQTT 开门命令
        future = mqtt_manager.register_open_confirmation(device.name)
        mqtt_manager.publish_command(device.name, "OPEN_DOOR")

        # 7. 等设备回复 OPENED（最长 5 秒）
        try:
            await asyncio.wait_for(future, timeout=5)
            # 设备确认开门成功
            _add_door_log(db, device_name, username, "成功", ip)
            invalidate_stat_cache(user_id)
            logger.info(f"开门成功 | 设备: {device_name} | 用户: {username} | 用户ID: {user_id}")
            return {
                "success": True,
                "message": "开门成功",
                "device_id": device.id,
                "username": username,
                "device_name": device_name,
                "location": device.location or "",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except asyncio.TimeoutError:
            # 设备未回复
            _add_door_log(db, device_name, username, "失败：设备无响应", ip)
            logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 设备无响应（超时）")
            raise TimeoutError(f"设备「{device_name}」未响应，开门失败")
    finally:
        # 释放分布式锁（仅释放自己加的锁，避免误删其他实例的锁）
        if redis_client:
            current_val = redis_client.get(lock_key)
            if current_val and current_val == lock_value:
                redis_client.delete(lock_key)
