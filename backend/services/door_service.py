from database.models.device import Device
from database.models.user import User
from database.models.door_log import DoorLog
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from services.device_service import check_user_permission
from services.mqtt_service import mqtt_manager
from services.stat_service import invalidate_stat_cache
from services.permission_service import user_has_permission
from utils.service_exception_handler import service_exception_handler
from schemas.door_schema import LogQuery
from utils.logger import AppLogger
from core.exceptions import NotFoundError
from database.redis import redis_client, cache_get_json, cache_set_json
import asyncio
import uuid

logger = AppLogger.get_logger()

# 远程开门冷却时间（秒）
DOOR_OPEN_COOLDOWN = 3

# 日志缓存配置
LOG_CACHE_TTL = 30  # 缓存30秒
LOG_CACHE_PREFIX = "cache:logs:"


def _add_door_log(db: Session, user_id: int, device_id: int, status: str, ip: str = None):
    """快速创建开门日志并提交"""
    db.add(DoorLog(
        user_id=user_id,
        device_id=device_id,
        action="远程开门",
        status=status,
        ip=ip,
        time=datetime.now()
    ))
    db.commit()

    # 清除日志缓存和异常事件缓存
    invalidate_log_cache()
    from services.alert_service import invalidate_alert_cache
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
        _add_door_log(db, user_id, device_id, "失败：设备不在线", ip)
        logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 设备不在线")
        raise PermissionError(f"设备「{device_name}」不在线，无法开门")

    # 3.1 Redis 实时在线检查（弥补 MySQL 状态更新延迟）
    if redis_client and not redis_client.exists(f"device:online:{device.name}"):
        _add_door_log(db, user_id, device_id, "失败：设备已断线", ip)
        logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: Redis 检测到设备离线")
        raise PermissionError(f"设备「{device_name}」已断线，无法开门")

    # 3.2 设备锁定检查（密码/指纹/刷卡错误5次后锁定）
    err_lock_key = f"door:err:lock:{device.name}"
    if redis_client and redis_client.exists(err_lock_key):
        lock_ttl = redis_client.ttl(err_lock_key)
        _add_door_log(db, user_id, device_id, f"失败：设备已锁定（剩余{lock_ttl}秒）", ip)
        logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 设备已锁定（剩余{lock_ttl}秒）")
        raise PermissionError(f"设备已锁定，请 {lock_ttl} 秒后再试")

    # 4. 权限判断（有 device.view 权限可操作任意设备，否则需绑定）
    if not user_has_permission(db, user, "device.view"):
        if not check_user_permission(db, user_id, device_id):
            _add_door_log(db, user_id, device_id, "失败：无权限，未绑定该设备", ip)
            logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 无权限")
            raise PermissionError("无权限操作：你未绑定该设备，无法开门")

    # ===== 分布式锁（设备级互斥，防止多人同时操作同一门禁） =====
    lock_key = f"door:lock:{device_id}"
    lock_value = str(uuid.uuid4())
    if redis_client:
        locked = redis_client.set(lock_key, lock_value, ex=5, nx=True)
        if not locked:
            _add_door_log(db, user_id, device_id, "失败：设备正在被操作", ip)
            logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 设备忙")
            raise PermissionError("该设备正在操作中，请稍后")

    try:
        # 5. 冷却时间检查（防止频繁开门）
        cooldown_key = f"door:cooldown:{user_id}:{device_id}"
        if redis_client:
            if redis_client.exists(cooldown_key):
                _add_door_log(db, user_id, device_id, "失败：操作过于频繁", ip)
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
            _add_door_log(db, user_id, device_id, "成功", ip)
            invalidate_stat_cache(user_id)
            logger.info(f"开门成功 | 设备: {device_name} | 用户: {username} | 用户ID: {user_id}")
            return {
                "success": True,
                "message": "开门成功",
                "device_id": device.id,
                "username": username,
                "device_name": device_name,
                "location": device.location or ""
            }
        except asyncio.TimeoutError:
            # 设备未回复
            _add_door_log(db, user_id, device_id, "失败：设备无响应", ip)
            logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 设备无响应（超时）")
            raise TimeoutError(f"设备「{device_name}」未响应，开门失败")
    finally:
        # 释放分布式锁（仅释放自己加的锁，避免误删其他实例的锁）
        if redis_client:
            current_val = redis_client.get(lock_key)
            if current_val and current_val == lock_value:
                redis_client.delete(lock_key)



# =================== 3. 日志查询功能======================
def _build_log_cache_key(user_id: int, params: LogQuery) -> str:
    """生成日志缓存键"""
    # 构造参数字符串用于生成唯一键
    parts = [
        f"u:{user_id}",
        f"p:{params.page}",
        f"s:{params.size}",
    ]
    if params.user_id:
        parts.append(f"uid:{params.user_id}")
    if params.device_name:
        parts.append(f"dev:{params.device_name}")
    if params.status:
        parts.append(f"st:{params.status}")
    if params.start_time:
        parts.append(f"from:{params.start_time}")
    if params.end_time:
        parts.append(f"to:{params.end_time}")

    return LOG_CACHE_PREFIX + ":".join(parts)


@service_exception_handler
def query_logs(
        db: Session,
        params: LogQuery,
        current_user_id: int
) -> tuple[int, list]:
    """
    查询门禁日志

    参数:
        db: 数据库会话
        params: LogQuery schema 对象
        current_user_id: 当前用户ID

    返回:
        (total, result): 总数和日志列表
    """
    # 尝试从缓存获取
    cache_key = _build_log_cache_key(current_user_id, params)
    cached = cache_get_json(cache_key)
    if cached is not None:
        logger.debug(f"日志缓存命中: {cache_key}")
        return cached["total"], cached["list"]

    # 缓存未命中，查询数据库
    # 基础查询 - 关联设备表获取设备信息
    query = db.query(
        DoorLog,
        Device.name.label("device_name"),
        Device.location.label("device_location"),
        User.username.label("username")
    ).outerjoin(Device, DoorLog.device_id == Device.id
    ).outerjoin(User, DoorLog.user_id == User.id)

    # 权限过滤：有 log.view 可看全部日志，否则只能看自己的
    from database.models.user import User as UserModel
    _user = db.query(UserModel).filter(UserModel.id == current_user_id).first()
    can_view_all = _user and user_has_permission(db, _user, "log.view")

    if not can_view_all:
        query = query.filter(DoorLog.user_id == current_user_id)

    # 构造查询条件
    conditions = []

    # 用户ID筛选（仅有 log.view 权限的用户可用）
    if params.user_id and can_view_all:
        conditions.append(DoorLog.user_id == params.user_id)

    # 设备名称模糊搜索
    if params.device_name:
        conditions.append(Device.name.contains(params.device_name))

    # 状态筛选（前缀匹配，如"失败"匹配"失败：无权限"）
    if params.status:
        conditions.append(DoorLog.status.startswith(params.status))

    # 时间范围筛选
    if params.start_time:
        conditions.append(DoorLog.time >= params.start_time)
    if params.end_time:
        conditions.append(DoorLog.time <= params.end_time)

    if conditions:
        query = query.filter(and_(*conditions))

    # 按时间倒序排列（最新的在前）
    query = query.order_by(DoorLog.time.desc())

    # 总数
    total = query.count()

    # 分页
    offset = (params.page - 1) * params.size
    logs = query.offset(offset).limit(params.size).all()

    # 格式化返回
    result = []
    for log, device_name, device_location, username in logs:
        result.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": "本地" if log.user_id is None else (username or "未知用户"),
            "device_id": log.device_id,
            "device_name": device_name or "未知设备",
            "device_location": device_location or "未知位置",
            "action": log.action,
            "status": log.status,
            "ip": log.ip or "",
            "time": str(log.time) if log.time else None
        })

    # 写入缓存
    cache_set_json(cache_key, {"total": total, "list": result}, LOG_CACHE_TTL)
    logger.debug(f"日志缓存写入: {cache_key}")

    return total, result


def invalidate_log_cache():
    """
    清除所有日志缓存
    在新增日志时调用
    """
    if not redis_client:
        return

    try:
        # 扫描并删除所有日志缓存键
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=f"{LOG_CACHE_PREFIX}*", count=100)
            if keys:
                redis_client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break

        if deleted > 0:
            logger.info(f"已清除 {deleted} 个日志缓存")
    except Exception as e:
        logger.warning(f"清除日志缓存失败: {e}")
