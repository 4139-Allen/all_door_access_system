from database.models.device import Device
from database.models.user_device import UserDevice
from database.models.user import User
from sqlalchemy.orm import Session
from schemas.device_schema import DeviceCreate, DeviceUpdate
from utils.service_exception_handler import service_exception_handler
from typing import Optional
from database.redis import redis_client, cache_get_json, cache_set_json
from utils.logger import AppLogger
from core.exceptions import NotFoundError
from services.stat_service import invalidate_all_stat_cache, invalidate_stat_cache
from services.permission_service import user_has_permission

logger = AppLogger.get_logger()

# ======================
# 缓存管理
# ======================
DEVICE_CACHE_KEY_TEMPLATE = "cache:device:list:user:{user_id}"
CACHE_EXPIRE = 60


def invalidate_device_cache(user_id: int):
    """清除指定用户的设备缓存"""
    if redis_client:
        cache_key = DEVICE_CACHE_KEY_TEMPLATE.format(user_id=user_id)
        redis_client.delete(cache_key)


def invalidate_all_device_cache():
    """清除所有用户的设备缓存（使用 SCAN 避免阻塞 Redis）"""
    if redis_client:
        pattern = "cache:device:list:user:*"
        keys = list(redis_client.scan_iter(pattern))
        if keys:
            redis_client.delete(*keys)


# ======================
# 权限检查
# ======================
def check_user_permission(db: Session, user_id: int, device_id: int) -> bool:
    """
    检查用户是否有权限访问指定设备

    参数:
        db: 数据库会话
        user_id: 用户ID
        device_id: 设备ID

    返回:
        bool: 是否有权限
    """
    bind = db.query(UserDevice).filter(
        UserDevice.user_id == user_id,
        UserDevice.device_id == device_id
    ).first()

    return bind is not None


# ======================
# 设备 CRUD
# ======================
@service_exception_handler
def create_device(db: Session, data: DeviceCreate) -> Device:
    """
    创建设备

    异常:
        ValueError: 设备名称或位置为空，或设备已存在
    """
    # 验证必填字段
    if not data.name or not data.name.strip():
        raise ValueError("设备名称不能为空")
    if not data.location or not data.location.strip():
        raise ValueError("设备位置不能为空")

    # 检查设备是否已存在
    exists = db.query(Device).filter(
        Device.name == data.name,
        Device.location == data.location
    ).first()
    if exists:
        logger.warning(f"⚠️  创建设备失败 | 设备名: {data.name} | 原因: 已存在")
        raise ValueError("该设备已存在，请勿重复添加")

    device = Device(
        name=data.name,
        location=data.location,
        status="offline"
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    # 清除所有用户的设备缓存
    invalidate_all_device_cache()
    invalidate_all_stat_cache()

    logger.info(f"📱 创建设备成功 | 设备名: {device.name} | 位置: {device.location} | 设备ID: {device.id}")
    return device


@service_exception_handler
def update_device(db: Session, device_id: int, data: DeviceUpdate) -> Device:
    device = db.query(Device).filter(Device.id == device_id).first()

    if not device:
        raise NotFoundError("设备不存在")

    if data.name is not None:
        device.name = data.name
    if data.status is not None:
        device.status = data.status
    if data.location is not None:
        device.location = data.location

    db.commit()
    db.refresh(device)

    # 清除所有用户的设备缓存
    invalidate_all_device_cache()
    invalidate_all_stat_cache()

    return device


@service_exception_handler
def delete_device(db: Session, device_id: int) -> bool:
    """
    删除设备

    参数:
        db: 数据库会话
        device_id: 设备ID

    返回:
        bool: 是否删除成功

    异常:
        ValueError: 设备不存在或已绑定用户
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        logger.warning(f"⚠️  删除设备失败 | 设备ID: {device_id} | 原因: 设备不存在")
        raise NotFoundError("设备不存在")

    # 检查是否有绑定关系
    has_bind = db.query(UserDevice).filter(UserDevice.device_id == device_id).first()
    if has_bind:
        logger.warning(f"⚠️  删除设备失败 | 设备: {device.name} | 原因: 已绑定用户")
        raise ValueError("该设备已绑定用户，无法删除")

    device_name = device.name
    db.delete(device)
    db.commit()

    # 清除所有用户的设备缓存
    invalidate_all_device_cache()
    invalidate_all_stat_cache()

    logger.info(f"🗑️  删除设备成功 | 设备名: {device_name} | 设备ID: {device_id}")
    return True


@service_exception_handler
def get_device_list(
    db: Session,
    current_user_id: int,
    role: str,
    name: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    current_user: User = None
    ) -> dict:
    # 只有无筛选且是第一页时才使用缓存
    use_cache = (name is None and page == 1 and size == 10)
    if use_cache:
        cache_key = DEVICE_CACHE_KEY_TEMPLATE.format(user_id=current_user_id)
        cached = cache_get_json(cache_key)
        if cached:
            return cached

    query = db.query(Device)

    if name:
        query = query.filter(Device.name.contains(name))

    # 有 device.view 权限可看全部设备，否则只能看绑定的
    can_view_all = current_user and user_has_permission(db, current_user, "device.view")
    if not can_view_all:
        query = query.filter(
            Device.id.in_(
                db.query(UserDevice.device_id).filter(UserDevice.user_id == current_user_id)
            )
        )

    # 分页
    total = query.count()
    skip = (page - 1) * size
    devices = query.offset(skip).limit(size).all()

    # 叠加 Redis 实时在线状态
    device_list = []
    for d in devices:
        live_status = d.status
        if d.status == "online" and redis_client:
            if not redis_client.exists(f"device:online:{d.name}"):
                live_status = "offline"
        device_list.append({
            "id": d.id,
            "name": d.name,
            "location": d.location,
            "status": live_status,
            "signal_strength": d.signal_strength,
            "last_online_at": d.last_online_at.strftime("%Y-%m-%d %H:%M:%S") if d.last_online_at else ""
        })

    result = {
        "total": total,
        "list": device_list
    }

    if use_cache:
        cache_set_json(DEVICE_CACHE_KEY_TEMPLATE.format(user_id=current_user_id), result, CACHE_EXPIRE)

    return result

# ======================
# 用户 <-> 设备 绑定/权限
# ======================
@service_exception_handler
def bind_user_device(db: Session, user_id: int, device_id: int, operator_id: Optional[int] = None) -> UserDevice:
    """
    绑定用户到设备

    参数:
        db: 数据库会话
        user_id: 要绑定的用户ID
        device_id: 设备ID
        operator_id: 操作者ID（用于清除缓存）

    异常:
        ValueError: 用户已绑定该设备
    """
    # 验证设备是否存在
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise NotFoundError("设备不存在")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("用户不存在")

    # 检查是否已存在绑定关系
    exists = db.query(UserDevice).filter(
        UserDevice.user_id == user_id,
        UserDevice.device_id == device_id
    ).first()

    if exists:
        logger.warning(f"⚠️  绑定失败 | 用户: {user.username} | 设备: {device.name} | 原因: 已绑定")
        raise ValueError("用户已绑定该设备")

    record = UserDevice(user_id=user_id, device_id=device_id)
    db.add(record)
    db.commit()
    db.refresh(record)

    # 清除相关用户的缓存
    invalidate_device_cache(user_id)
    invalidate_stat_cache(user_id)
    if operator_id and operator_id != user_id:
        invalidate_device_cache(operator_id)

    logger.info(f"🔗 绑定设备成功 | 用户: {user.username} | 设备: {device.name} | 设备ID: {device_id}")
    return record


@service_exception_handler
def unbind_user_device(db: Session, user_id: int, device_id: int, operator_id: Optional[int] = None) -> bool:
    """
    解除用户与设备的绑定

    参数:
        db: 数据库会话
        user_id: 用户ID
        device_id: 设备ID
        operator_id: 操作者ID（用于清除缓存）

    返回:
        bool: 是否解绑成功

    异常:
        ValueError: 绑定关系不存在
    """
    bind = db.query(UserDevice).filter(
        UserDevice.user_id == user_id,
        UserDevice.device_id == device_id
    ).first()

    if not bind:
        raise ValueError("该绑定关系不存在")

    # 获取用户和设备信息
    user = db.query(User).filter(User.id == user_id).first()
    device = db.query(Device).filter(Device.id == device_id).first()
    username = user.username if user else f"用户ID:{user_id}"
    device_name = device.name if device else f"设备ID:{device_id}"

    db.delete(bind)
    db.commit()

    # 清除相关用户的缓存
    invalidate_device_cache(user_id)
    invalidate_stat_cache(user_id)
    if operator_id and operator_id != user_id:
        invalidate_device_cache(operator_id)

    logger.info(f"🔓 解绑设备成功 | 用户: {username} | 设备: {device_name} | 设备ID: {device_id}")
    return True
