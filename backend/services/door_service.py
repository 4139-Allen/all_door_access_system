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

logger = AppLogger.get_logger()


def _add_door_log(db: Session, user_id: int, device_id: int, status: str, ip: str = None):
    """快速创建开门日志并提交"""
    db.add(DoorLog(
        user_id=user_id,
        device_id=device_id,
        action="开门",
        status=status,
        ip=ip,
        time=datetime.now()
    ))
    db.commit()


# ==========================================
# 1. 开门核心逻辑
# ==========================================
@service_exception_handler
def open_door_service(db: Session, user_id: int, device_id: int, ip: str = None) -> dict:
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

    # 4. 权限判断（有 device.view 权限可操作任意设备，否则需绑定）
    if not user_has_permission(db, user, "device.view"):
        if not check_user_permission(db, user_id, device_id):
            _add_door_log(db, user_id, device_id, "失败：无权限，未绑定该设备", ip)
            logger.warning(f"开门失败 | 设备: {device_name} | 用户: {username} | 原因: 无权限")
            raise PermissionError("无权限操作：你未绑定该设备，无法开门")

    # 5. 开门成功
    _add_door_log(db, user_id, device_id, "成功", ip)

    # 6. 清除统计数据缓存
    invalidate_stat_cache(user_id)

    # 7. 发送 MQTT 开门命令给硬件设备
    mqtt_manager.publish_command(device.name, "OPEN_DOOR")

    logger.info(f"开门成功 | 设备: {device_name} | 用户: {username} | 用户ID: {user_id}")

    return {
        "success": True,
        "message": "开门成功",
        "device_id": device.id,
        "username": username,
        "device_name": device_name,
        "location": device.location or ""
    }



# =================== 3. 日志查询功能======================
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
        role: 用户角色

    返回:
        (total, result): 总数和日志列表
    """
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

    return total, result
