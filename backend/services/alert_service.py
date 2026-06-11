"""
异常事件服务层
处理设备锁定、安全告警等异常事件的业务逻辑
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from database.models.door_log import DoorLog
from database.models.device import Device
from database.models.user import User
from database.redis import redis_client, cache_get_json, cache_set_json
from services.permission_service import user_has_permission
from services.mqtt_service import mqtt_manager
from utils.service_exception_handler import service_exception_handler
from utils.logger import AppLogger

logger = AppLogger.get_logger()

# 异常事件缓存配置
ALERT_CACHE_TTL = 30  # 缓存30秒
ALERT_CACHE_PREFIX = "cache:alerts:"


def _build_alert_cache_key(user_id: int, page: int, size: int, device_name: Optional[str],
                           alert_type: Optional[str], start_time: Optional[str], end_time: Optional[str]) -> str:
    """生成异常事件缓存键"""
    parts = [
        f"u:{user_id}",
        f"p:{page}",
        f"s:{size}",
    ]
    if device_name:
        parts.append(f"dev:{device_name}")
    if alert_type:
        parts.append(f"type:{alert_type}")
    if start_time:
        parts.append(f"from:{start_time}")
    if end_time:
        parts.append(f"to:{end_time}")

    return ALERT_CACHE_PREFIX + ":".join(parts)


@service_exception_handler
def get_alert_list(
    db: Session,
    current_user: User,
    page: int = 1,
    size: int = 10,
    device_name: Optional[str] = None,
    alert_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> tuple[int, list]:
    """
    获取异常事件列表

    Args:
        db: 数据库会话
        current_user: 当前用户
        page: 页码
        size: 每页数量
        device_name: 设备名称筛选
        alert_type: 事件类型 (lock/offline/error)
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        (total, result): 总数和事件列表
    """
    # 尝试从缓存获取
    cache_key = _build_alert_cache_key(current_user.id, page, size, device_name, alert_type, start_time, end_time)
    cached = cache_get_json(cache_key)
    if cached is not None:
        logger.debug(f"异常事件缓存命中: {cache_key}")
        return cached["total"], cached["list"]

    # 缓存未命中，查询数据库
    # 基础查询
    query = db.query(
        DoorLog,
        Device.name.label("device_name"),
        Device.location.label("device_location"),
        User.username.label("username")
    ).outerjoin(Device, DoorLog.device_id == Device.id
    ).outerjoin(User, DoorLog.user_id == User.id)

    # 权限过滤：有 alert.view 权限可看全部日志，否则只能看自己的
    if not user_has_permission(db, current_user, "alert.view"):
        query = query.filter(DoorLog.user_id == current_user.id)

    # 构造查询条件
    conditions = []

    # 事件类型筛选
    if alert_type == "lock":
        conditions.append(DoorLog.status.contains("锁定"))
    elif alert_type == "offline":
        conditions.append(DoorLog.status.contains("设备不在线"))
    elif alert_type == "error":
        conditions.append(DoorLog.status.startswith("失败"))
    else:
        # 默认显示所有异常事件
        conditions.append(or_(
            DoorLog.status.startswith("失败"),
            DoorLog.status.contains("锁定")
        ))

    # 设备名称筛选
    if device_name:
        conditions.append(Device.name.contains(device_name))

    # 时间范围筛选
    if start_time:
        conditions.append(DoorLog.time >= start_time)
    if end_time:
        conditions.append(DoorLog.time <= end_time)

    if conditions:
        query = query.filter(and_(*conditions))

    # 按时间倒序
    query = query.order_by(DoorLog.time.desc())

    # 总数
    total = query.count()

    # 分页
    offset = (page - 1) * size
    alerts = query.offset(offset).limit(size).all()

    # 格式化返回
    result = []
    for log, device_name, device_location, username in alerts:
        # 判断事件类型和级别
        event_type = "error"
        event_level = "warning"
        if "锁定" in log.status:
            event_type = "lock"
            event_level = "danger"
        elif "设备不在线" in log.status:
            event_type = "offline"
            event_level = "warning"

        result.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": "本地" if log.user_id is None else (username or "未知用户"),
            "device_id": log.device_id,
            "device_name": device_name or "未知设备",
            "device_location": device_location or "未知位置",
            "action": log.action,
            "status": log.status,
            "event_type": event_type,
            "event_level": event_level,
            "ip": log.ip or "",
            "time": str(log.time) if log.time else None
        })

    # 写入缓存
    cache_set_json(cache_key, {"total": total, "list": result}, ALERT_CACHE_TTL)
    logger.debug(f"异常事件缓存写入: {cache_key}")

    return total, result


@service_exception_handler
def get_alert_stats(db: Session, hours: int = 24) -> dict:
    """
    获取异常事件统计

    Args:
        db: 数据库会话
        hours: 统计时间范围（小时）

    Returns:
        dict: 统计数据
    """
    time_threshold = datetime.now() - timedelta(hours=hours)

    # 基础查询
    base_query = db.query(DoorLog).filter(DoorLog.time >= time_threshold)

    # 总异常数
    total_alerts = base_query.filter(or_(
        DoorLog.status.startswith("失败"),
        DoorLog.status.contains("锁定")
    )).count()

    # 设备锁定次数
    lock_count = base_query.filter(DoorLog.status.contains("锁定")).count()

    # 开门失败次数
    error_count = base_query.filter(DoorLog.status.startswith("失败")).count()

    # 各设备异常分布
    device_stats = db.query(
        Device.name,
        func.count(DoorLog.id).label('count')
    ).join(DoorLog, DoorLog.device_id == Device.id
    ).filter(
        DoorLog.time >= time_threshold,
        or_(
            DoorLog.status.startswith("失败"),
            DoorLog.status.contains("锁定")
        )
    ).group_by(Device.name).all()

    # 获取当前锁定的设备
    locked_devices = _get_locked_devices(db)

    return {
        "total_alerts": total_alerts,
        "lock_count": lock_count,
        "error_count": error_count,
        "device_stats": [{"name": name, "count": count} for name, count in device_stats],
        "locked_devices": locked_devices,
        "time_range_hours": hours
    }


@service_exception_handler
def unlock_device(db: Session, device_name: str) -> str:
    """
    解除设备密码锁定

    Args:
        db: 数据库会话
        device_name: 设备名称

    Returns:
        str: 成功消息
    """
    # 检查设备是否存在
    device = db.query(Device).filter(Device.name == device_name).first()
    if not device:
        raise ValueError("设备不存在")

    # 删除 Redis 锁定键
    if redis_client:
        lock_key = f"door:err:lock:{device_name}"
        if redis_client.exists(lock_key):
            redis_client.delete(lock_key)
        # 也删除失败计数
        fail_key = f"door:err:fail:{device_name}"
        redis_client.delete(fail_key)

    # 发送 UNLOCK 命令给 STM32
    mqtt_manager.publish_command(device_name, "UNLOCK")

    logger.info(f"设备锁定已解除: {device_name}")
    return f"设备 {device_name} 锁定已解除"


def _get_locked_devices(db: Session) -> list:
    """获取当前锁定的设备列表"""
    locked_devices = []
    if not redis_client:
        return locked_devices

    # 扫描所有锁定键
    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor, match="door:err:lock:*", count=100)
        for key in keys:
            device_name = key.split(":")[-1]
            ttl = redis_client.ttl(key)
            device = db.query(Device).filter(Device.name == device_name).first()
            if device:
                locked_devices.append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "device_location": device.location or "",
                    "lock_ttl": ttl
                })
        if cursor == 0:
            break

    return locked_devices


def invalidate_alert_cache():
    """
    清除所有异常事件缓存
    在新增异常事件时调用
    """
    if not redis_client:
        return

    try:
        # 扫描并删除所有异常事件缓存键
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=f"{ALERT_CACHE_PREFIX}*", count=100)
            if keys:
                redis_client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break

        if deleted > 0:
            logger.info(f"已清除 {deleted} 个异常事件缓存")
    except Exception as e:
        logger.warning(f"清除异常事件缓存失败: {e}")