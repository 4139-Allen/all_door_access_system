import re

from database.models.device import Device
from database.models.user import User
from database.models.door_log import DoorLog
from sqlalchemy.orm import Session
from sqlalchemy import and_
from utils.service_exception_handler import service_exception_handler
from schemas.door_schema import LogQuery
from utils.logger import AppLogger
from database.redis import redis_client, cache_get_json, cache_set_json

logger = AppLogger.get_logger()

# 软删除用户 username 格式：deleted_{id}_{original_name}
_DELETED_USER_RE = re.compile(r'^deleted_\d+_(.*)$')

# 日志缓存配置
LOG_CACHE_TTL = 30  # 缓存30秒
LOG_CACHE_PREFIX = "cache:logs:"


def _build_log_cache_key(user_id: int, params: LogQuery) -> str:
    """生成日志缓存键"""
    parts = [
        f"u:{user_id}",
        f"p:{params.page}",
        f"s:{params.size}",
    ]
    if params.username:
        parts.append(f"uname:{params.username}")
    if params.device_name:
        parts.append(f"dev:{params.device_name}")
    if params.status:
        parts.append(f"st:{params.status}")
    if params.start_time:
        parts.append(f"from:{params.start_time}")
    if params.end_time:
        parts.append(f"to:{params.end_time}")

    return LOG_CACHE_PREFIX + ":".join(parts)


def _build_admin_log_msg(params: LogQuery, total: int, log_list_len: int) -> str:
    """生成管理员日志列表的消息"""
    filters = []
    if params.username:
        filters.append("指定用户名")
    if params.device_name:
        filters.append("指定设备")
    if params.status:
        filters.append(f"状态「{params.status}」")
    if params.start_time and params.end_time:
        filters.append("时间范围")
    elif params.start_time:
        filters.append("开始时间")
    elif params.end_time:
        filters.append("结束时间")

    if total == 0:
        if not filters:
            return "日志记录为空"
        return f"已筛选{'、'.join(filters)}，没有找到符合条件的记录"
    if log_list_len == 0:
        return f"当前页无数据，共 {total} 条记录"
    if not filters:
        return f"获取日志成功，共 {total} 条"
    return f"已筛选{'、'.join(filters)}，共 {total} 条"


def _build_my_log_msg(total: int, log_list_len: int) -> str:
    """生成个人日志列表的消息"""
    if total == 0:
        return "暂无开门记录"
    if log_list_len == 0:
        return f"当前页无数据，共 {total} 条记录"
    return f"获取日志成功，共 {total} 条"


@service_exception_handler
def query_logs(
        db: Session,
        params: LogQuery,
        current_user_id: int,
        can_view_all: bool = False
) -> tuple[int, list]:
    """
    查询门禁日志

    参数:
        db: 数据库会话
        params: LogQuery schema 对象
        current_user_id: 当前用户ID
        can_view_all: 是否可查看全部日志（由 API 层根据权限传入）

    返回:
        (total, result): 总数和日志列表
    """
    cache_key = _build_log_cache_key(current_user_id, params)
    cached = cache_get_json(cache_key)
    if cached is not None:
        logger.debug(f"日志缓存命中: {cache_key}")
        return cached["total"], cached["list"]

    query = db.query(
        DoorLog,
        Device.name.label("device_name"),
        Device.location.label("device_location"),
        User.username.label("username"),
        User.is_active.label("user_is_active")
    ).outerjoin(Device, DoorLog.device_id == Device.id
    ).outerjoin(User, DoorLog.user_id == User.id)

    if not can_view_all:
        query = query.filter(DoorLog.user_id == current_user_id)

    conditions = []
    if params.username and can_view_all:
        conditions.append(User.username.contains(params.username, autoescape=True))
    if params.device_name:
        conditions.append(Device.name.contains(params.device_name, autoescape=True))
    if params.status:
        conditions.append(DoorLog.status.startswith(params.status, autoescape=True))
    if params.start_time:
        conditions.append(DoorLog.time >= params.start_time)
    if params.end_time:
        conditions.append(DoorLog.time <= params.end_time)
    if conditions:
        query = query.filter(and_(*conditions))

    query = query.order_by(DoorLog.time.desc())

    total = query.count()
    offset = (params.page - 1) * params.size
    logs = query.offset(offset).limit(params.size).all()

    result = []
    for log, device_name, device_location, username, user_is_active in logs:
        if log.user_id is None:
            display_name = "本地"
        elif not username:
            display_name = "未知用户"
        elif user_is_active is False:
            m = _DELETED_USER_RE.match(username)
            display_name = f"{m.group(1)}（已停用）" if m else username
        else:
            display_name = username

        result.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": display_name,
            "device_id": log.device_id,
            "device_name": device_name or "未知设备",
            "device_location": device_location or "未知位置",
            "action": log.action,
            "status": log.status,
            "ip": log.ip or "",
            "time": str(log.time) if log.time else None
        })

    cache_set_json(cache_key, {"total": total, "list": result}, LOG_CACHE_TTL)
    logger.debug(f"日志缓存写入: {cache_key}")

    return total, result


@service_exception_handler
def export_logs(
    db: Session,
    params: LogQuery,
    current_user_id: int,
    can_view_all: bool = False
) -> list[dict]:
    """导出门禁日志（不分页，用于生成 Excel）"""
    query = db.query(
        DoorLog,
        Device.name.label("device_name"),
        Device.location.label("device_location"),
        User.username.label("username"),
        User.is_active.label("user_is_active")
    ).outerjoin(Device, DoorLog.device_id == Device.id
    ).outerjoin(User, DoorLog.user_id == User.id)

    if not can_view_all:
        query = query.filter(DoorLog.user_id == current_user_id)

    conditions = []
    if params.username and can_view_all:
        conditions.append(User.username.contains(params.username, autoescape=True))
    if params.device_name:
        conditions.append(Device.name.contains(params.device_name, autoescape=True))
    if params.status:
        conditions.append(DoorLog.status.startswith(params.status, autoescape=True))
    if params.start_time:
        conditions.append(DoorLog.time >= params.start_time)
    if params.end_time:
        conditions.append(DoorLog.time <= params.end_time)
    if conditions:
        query = query.filter(and_(*conditions))

    query = query.order_by(DoorLog.time.desc())
    logs = query.all()

    result = []
    for log, device_name, device_location, username, user_is_active in logs:
        if log.user_id is None:
            display_name = "本地"
        elif not username:
            display_name = "未知用户"
        elif user_is_active is False:
            m = _DELETED_USER_RE.match(username)
            display_name = f"{m.group(1)}（已停用）" if m else username
        else:
            display_name = username

        result.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": display_name,
            "device_name": device_name or "未知设备",
            "device_location": device_location or "未知位置",
            "action": log.action,
            "status": log.status,
            "ip": log.ip or "",
            "time": str(log.time) if log.time else None
        })

    return result


def invalidate_log_cache():
    """清除所有日志缓存"""
    if not redis_client:
        return

    try:
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
