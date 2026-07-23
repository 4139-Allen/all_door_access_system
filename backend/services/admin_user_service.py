import random
import re
from datetime import datetime

from sqlalchemy.orm import Session

from core.config import AUTO_CREATE_ADMIN, ADMIN_USERNAME, ADMIN_PASSWORD
from core.exceptions import NotFoundError
from utils.service_exception_handler import service_exception_handler
from database.db import SessionLocal
from database.models.user import User
from database.models.role import Role
from database.models.door_log import DoorLog
from database.models.user_device import UserDevice
from utils.auth import verify_password, hash_password, build_login_response
from typing import Optional
from utils.logger import AppLogger
from database.redis import redis_client, cache_get_json, cache_set_json
from services.stat_service import invalidate_all_stat_cache
from services.permission_service import invalidate_user_perm_cache
from schemas.user_schema import UserCreate

logger = AppLogger.get_logger()

# ==================== 缓存配置 ====================
USER_LIST_CACHE_KEY = "cache:user:list:page:{page}:size:{size}:user:{username}:role:{role}"
USER_PROFILE_CACHE_KEY = "cache:user:profile:{user_id}"
USER_CACHE_TTL = 60  # 用户列表缓存 60 秒
USER_PROFILE_CACHE_TTL = 300  # 个人信息缓存 5 分钟

# 随机 TTL 偏移比例（±20%），防止缓存击穿
TTL_JITTER = 0.2


def _random_ttl(base: int) -> int:
    """在 base TTL 上加 ±20% 随机偏移，避免多个缓存同时过期"""
    offset = int(base * TTL_JITTER)
    return base + random.randint(-offset, offset)


def _invalidate_user_list_cache():
    """清除所有用户列表缓存（创建/删除/修改用户后调用）"""
    if not redis_client:
        return
    try:
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match="cache:user:list:*", count=100)
            if keys:
                redis_client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        if deleted > 0:
            logger.debug(f"已清除 {deleted} 个用户列表缓存")
    except Exception as e:
        logger.warning(f"清除用户列表缓存失败: {e}")


def _resolve_user_by_credential(db: Session, credential: str):
    """
    根据凭据自动识别类型并查找用户

    优先按类型查对应字段，未命中时降级按用户名查找（兼容用户名为纯数字的场景）
    """
    credential = credential.strip()
    # 手机号 → 查 phone 字段
    if re.match(r'^1[3-9]\d{9}$', credential):
        user = db.query(User).filter(User.phone == credential).first()
        if user:
            return user
        # 没查到则当用户名处理
    # 邮箱 → 查 email 字段
    elif '@' in credential:
        user = db.query(User).filter(User.email == credential).first()
        if user:
            return user
        # 没查到则当用户名处理
    # 默认按用户名查
    return db.query(User).filter(User.username == credential).first()


@service_exception_handler
def login_user(db: Session, credential: str, password: str) -> dict:
    """
    统一密码登录（自动识别手机号/邮箱/用户名）

    返回:
        dict: {"token", "role", "username", "avatar"}

    异常:
        ValueError: 用户不存在/密码错误/未设置密码
    """
    user = _resolve_user_by_credential(db, credential)

    if not user:
        raise ValueError("用户不存在")

    if not user.is_active:
        raise ValueError("账号已被停用")

    if not user.password:
        raise ValueError("该账号未设置密码，请使用验证码登录")

    if not verify_password(password, user.password):
        raise ValueError("密码错误")

    logger.info(f"用户登录成功 | 用户名: {user.username} | 用户ID: {user.id}")
    return build_login_response(user, db=db)


@service_exception_handler
def db_create_user(db: Session, username: str, password: str = None, role: str = "user", phone: str = None, email: str = None, action: str = "创建") -> User:
    """
    创建新用户

    参数:
        db: 数据库会话
        username: 用户名
        password: 密码（可选，None 表示未设置密码）
        role: 角色，默认为 user
        phone: 手机号（可选）
        email: 邮箱（可选）
        action: 操作类型日志前缀，管理员调用为"创建"，用户注册调用为"注册"

    返回:
        User: 创建的用户对象

    异常:
        ValueError: 用户名已存在
    """
    username = username.strip()
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        logger.warning(f"⚠️  {action}用户失败 | 用户名: {username} | 原因: 已存在")
        raise ValueError(f"用户名 '{username}' 已存在")

    if phone:
        existing_phone = db.query(User).filter(User.phone == phone).first()
        if existing_phone:
            raise ValueError("该手机号已被注册")

    if email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise ValueError("该邮箱已被注册")

    hashed = hash_password(password) if password else None
    user = User(username=username, password=hashed, role=role, phone=phone, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    invalidate_all_stat_cache()
    _invalidate_user_list_cache()

    logger.info(f"👤 {action}用户成功 | 用户名: {username} | 角色: {role} | 用户ID: {user.id}")
    return user


@service_exception_handler
def bulk_create_users(db: Session, user_list: list[UserCreate]) -> dict:
    """
    批量创建用户（一次事务提交）

    参数:
        db: 数据库会话
        user_list: 已通过 Pydantic 验证的用户数据列表

    返回:
        dict: {"success_count": int, "fail_list": list[str]}
    """
    if not user_list:
        return {"success_count": 0, "fail_list": []}

    # 1. 批量查重：一次查询找出所有已存在的用户名
    usernames = [u.username for u in user_list]
    existing = db.query(User.username).filter(User.username.in_(usernames)).all()
    existing_set = {row[0] for row in existing}

    # 2. 分离成功和失败（同时检测文件内重复）
    users_to_create = []
    fail_list = []
    seen_in_file = set()
    for u in user_list:
        if u.username in seen_in_file:
            fail_list.append(f"用户名 '{u.username}' 在文件中重复")
        elif u.username in existing_set:
            fail_list.append(f"用户名 '{u.username}' 已存在")
        else:
            seen_in_file.add(u.username)
            users_to_create.append(u)

    # 3. 批量哈希密码 + 构建对象
    new_users = []
    for u in users_to_create:
        hashed = hash_password(u.password)
        new_users.append(User(username=u.username, password=hashed, role=u.role))

    # 4. 一次插入 + 一次提交
    if new_users:
        db.add_all(new_users)
        db.commit()

    invalidate_all_stat_cache()
    _invalidate_user_list_cache()

    logger.info(f"📦 批量创建用户 | 成功: {len(new_users)} | 失败: {len(fail_list)}")
    return {"success_count": len(new_users), "fail_list": fail_list}


@service_exception_handler
def delete_user_by_id(db: Session, user_id: int, current_user: User = None) -> bool:
    """
    停用用户（软删除）

    参数:
        db: 数据库会话
        user_id: 用户ID
        current_user: 当前操作用户

    返回:
        bool: 是否删除成功

    异常:
        ValueError: 不能删除自己、不能删除管理员
        NotFoundError: 用户不存在
    """
    # 不能删除自己
    if current_user and current_user.id == user_id:
        raise ValueError("不能删除自己")

    # 先检查用户是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"⚠️  停用用户失败 | 用户ID: {user_id} | 原因: 用户不存在")
        raise NotFoundError("用户不存在")

    # 不能删除管理员
    if user.role == "admin":
        raise ValueError("无权删除超级管理员")

    if not user.is_active:
        raise ValueError("该用户已被停用")

    username = user.username

    # 软删除：打标记 + 释放唯一约束
    user.is_active = False
    user.deleted_at = datetime.now()
    user.username = f"deleted_{user.id}_{user.username}"[:50]  # 释放用户名，截断到字段长度

    # 释放手机号和邮箱（如果有的话）
    user.phone = None
    user.email = None

    # 解绑所有设备
    db.query(UserDevice).filter(UserDevice.user_id == user_id).delete()

    db.commit()

    invalidate_all_stat_cache()
    _invalidate_user_list_cache()
    # 清除该用户的个人信息缓存
    redis_client.delete(USER_PROFILE_CACHE_KEY.format(user_id=user_id))

    logger.info(f"🗑️  停用用户成功 | 用户名: {username} | 用户ID: {user_id}")
    return True


@service_exception_handler
def update_user_role(db: Session, user_id: int, new_role: str, current_user: User) -> dict:
    """
    修改用户角色

    参数:
        db: 数据库会话
        user_id: 目标用户 ID
        new_role: 新角色标识（如 "operator"）
        current_user: 当前操作用户

    返回:
        dict: {"user_id", "username", "role", "role_name"}

    异常:
        ValueError: 不能修改自己、角色不存在、不能降级最后一个管理员
        NotFoundError: 用户不存在
    """
    # 不能修改自己的角色
    if current_user.id == user_id:
        raise ValueError("不能修改自己的角色")

    # 查询目标用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("用户不存在")

    # 超级管理员角色不可修改
    if user.role == "admin":
        raise ValueError("超级管理员角色不可修改")

    # 查询角色是否存在
    role_obj = db.query(Role).filter(Role.code == new_role).first()
    if not role_obj:
        raise ValueError(f"角色 '{new_role}' 不存在")

    # 角色没变则直接返回
    if user.role == new_role:
        return {"user_id": user.id, "username": user.username, "role": user.role, "role_name": role_obj.name}

    # 更新角色
    old_role = user.role
    user.role = new_role
    db.commit()

    # 清除该用户的权限缓存
    invalidate_user_perm_cache(user_id)
    # 清除角色变更后的缓存（用户列表 + 个人信息）
    _invalidate_user_list_cache()
    redis_client.delete(USER_PROFILE_CACHE_KEY.format(user_id=user_id))

    logger.info(f"✅ 修改用户角色成功 | 用户ID: {user_id} | {old_role} → {new_role}")
    return {"user_id": user.id, "username": user.username, "role": new_role, "role_name": role_obj.name}


@service_exception_handler
def get_users_list(db: Session, page: int, size: int, username: Optional[str] = None, role: Optional[str] = None,
                   show_inactive: bool = False) -> tuple[int, list]:
    """
    获取用户列表（支持分页和筛选）

    参数:
        db: 数据库会话
        page: 页码
        size: 每页数量
        username: 用户名模糊搜索
        role: 角色筛选
        show_inactive: 是否显示已停用用户（默认 False 只显示正常用户）

    返回:
        (total, users): 总数和用户列表
    """
    query = db.query(User)

    if not show_inactive:
        query = query.filter(User.is_active == True)

    if username:
        query = query.filter(User.username.contains(username))
    if role:
        query = query.filter(User.role == role)

    total = query.count()
    users = query.offset((page - 1) * size).limit(size).all()

    return total, users


def get_users_list_formatted(db: Session, page: int, size: int, username: Optional[str] = None, role: Optional[str] = None,
                              show_inactive: bool = False) -> dict:
    """获取用户列表（带格式化，直接返回可响应的数据）"""
    from database.models.role import Role

    # 无筛选条件时才使用缓存（仅活跃用户列表可缓存）
    use_cache = (username is None and role is None and not show_inactive)
    if use_cache:
        cache_key = USER_LIST_CACHE_KEY.format(page=page, size=size, username="none", role="none")
        cached = cache_get_json(cache_key)
        if cached is not None:
            return cached

    total, users = get_users_list(db, page, size, username, role, show_inactive=show_inactive)

    # 批量查询角色名称
    role_codes = {u.role for u in users}
    roles = db.query(Role.code, Role.name).filter(Role.code.in_(role_codes)).all()
    role_name_map = {r.code: r.name for r in roles}

    result = {
        "total": total,
        "list": [{
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "role_name": role_name_map.get(u.role, u.role),
            "avatar": u.avatar or "",
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else ""
        } for u in users]
    }

    if use_cache:
        cache_set_json(cache_key, result, _random_ttl(USER_CACHE_TTL))

    return result


@service_exception_handler
def import_users_from_bytes(db: Session, file_contents: bytes, filename: str = "") -> dict:
    """
    从 Excel 文件字节流批量导入用户

    参数:
        db: 数据库会话
        file_contents: Excel 文件内容（bytes）
        filename: 原始文件名（用于校验扩展名）

    返回:
        dict: {"success_count", "fail_count", "fail_list", "msg"}

    异常:
        ValueError: 文件格式不正确或数据为空
    """
    import io
    import openpyxl

    if filename and not filename.endswith(('.xlsx', '.xls')):
        raise ValueError("仅支持 .xlsx / .xls 格式")

    wb = openpyxl.load_workbook(io.BytesIO(file_contents), read_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        raise ValueError("Excel 中没有数据")

    valid_users = []
    fail_list = []

    for i, row in enumerate(rows, start=2):
        username = str(row[0]).strip() if row[0] else ""
        password = str(row[1]).strip() if len(row) > 1 and row[1] else "123456"

        if not username:
            fail_list.append(f"第{i}行：用户名为空")
            continue

        try:
            validated = UserCreate(username=username, password=password)
            valid_users.append(validated)
        except Exception as e:
            fail_list.append(f"第{i}行：{str(e)}")

    wb.close()

    result = bulk_create_users(db, valid_users)
    success_count = result["success_count"]
    fail_list.extend(result["fail_list"])

    msg = f"成功导入 {success_count} 个用户"
    if fail_list:
        msg += f"，{len(fail_list)} 个失败"

    return {
        "success_count": success_count,
        "fail_count": len(fail_list),
        "fail_list": fail_list,
        "msg": msg
    }


@service_exception_handler
def get_user_devices(db: Session, user_id: int) -> list:
    """
    获取用户绑定的设备ID列表

    参数:
        db: 数据库会话
        user_id: 用户ID

    返回:
        list: 设备ID列表
    """
    binds = db.query(UserDevice).filter(UserDevice.user_id == user_id).all()
    return [b.device_id for b in binds]


def get_user_profile(user: User, db: Session) -> dict:
    """获取用户个人信息（带 Redis 缓存）"""
    cache_key = USER_PROFILE_CACHE_KEY.format(user_id=user.id)
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    from database.models.role import Role
    role_obj = db.query(Role.name).filter(Role.code == user.role).first()
    role_name = role_obj.name if role_obj else user.role

    result = {
        "id": user.id,
        "username": user.username,
        "phone": user.phone or "",
        "email": user.email or "",
        "role": user.role,
        "role_name": role_name,
        "avatar": user.avatar,
        "has_password": bool(user.password),
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else None
    }

    cache_set_json(cache_key, result, _random_ttl(USER_PROFILE_CACHE_TTL))
    return result


@service_exception_handler
def update_username(db: Session, user: User, new_username: str) -> None:
    """修改用户名"""
    new_username = new_username.strip()
    if new_username == user.username:
        raise ValueError("新用户名与当前用户名相同")

    existing = db.query(User).filter(User.username == new_username).first()
    if existing:
        raise ValueError(f"用户名 '{new_username}' 已被使用")

    user.username = new_username
    db.commit()

    # 清除缓存
    _invalidate_user_list_cache()
    redis_client.delete(USER_PROFILE_CACHE_KEY.format(user_id=user.id))

    logger.info(f"用户修改用户名 | 用户ID: {user.id} | 新用户名: {new_username}")


@service_exception_handler
def bind_phone(db: Session, user: User, phone: str, code: str) -> None:
    """绑定手机号（需验证码确认）"""
    from services.verify_code_service import check_sms_code

    if not re.match(r'^1[3-9]\d{9}$', phone):
        raise ValueError("请输入正确的手机号")

    if not check_sms_code(phone, code):
        raise ValueError("验证码错误或已过期")

    # 检查手机号是否被其他用户绑定
    existing = db.query(User).filter(User.phone == phone, User.id != user.id).first()
    if existing:
        raise ValueError("该手机号已被其他账号绑定")

    user.phone = phone
    db.commit()
    redis_client.delete(USER_PROFILE_CACHE_KEY.format(user_id=user.id))
    logger.info(f"用户绑定手机号 | 用户ID: {user.id} | 手机号: {phone}")


@service_exception_handler
def bind_email(db: Session, user: User, email: str, code: str) -> None:
    """绑定邮箱（需验证码确认）"""
    from services.verify_code_service import verify_code

    if not verify_code(email, code):
        raise ValueError("验证码错误或已过期")

    # 检查邮箱是否被其他用户绑定
    existing = db.query(User).filter(User.email == email, User.id != user.id).first()
    if existing:
        raise ValueError("该邮箱已被其他账号绑定")

    user.email = email
    db.commit()
    redis_client.delete(USER_PROFILE_CACHE_KEY.format(user_id=user.id))
    logger.info(f"用户绑定邮箱 | 用户ID: {user.id} | 邮箱: {email}")


@service_exception_handler
def unbind_phone(db: Session, user: User) -> None:
    """解绑手机号"""
    if not user.phone:
        raise ValueError("未绑定手机号")
    user.phone = None
    db.commit()
    redis_client.delete(USER_PROFILE_CACHE_KEY.format(user_id=user.id))
    logger.info(f"用户解绑手机号 | 用户ID: {user.id}")


@service_exception_handler
def unbind_email(db: Session, user: User) -> None:
    """解绑邮箱"""
    if not user.email:
        raise ValueError("未绑定邮箱")
    user.email = None
    db.commit()
    redis_client.delete(USER_PROFILE_CACHE_KEY.format(user_id=user.id))
    logger.info(f"用户解绑邮箱 | 用户ID: {user.id}")


@service_exception_handler
def update_avatar(db: Session, user: User, avatar_path: str) -> None:
    """更新头像路径"""
    user.avatar = avatar_path
    db.commit()
    logger.info(f"用户更新头像 | 用户ID: {user.id}")


@service_exception_handler
def change_user_password(db: Session, user: User, old_password: str | None, new_password: str) -> bool:
    """
    修改用户密码

    参数:
        db: 数据库会话
        user: 用户对象
        old_password: 原密码（可为 None，表示用户未设置过密码）
        new_password: 新密码

    返回:
        bool: 是否修改成功

    异常:
        ValueError: 原密码错误或密码长度不符合要求
    """
    # 如果用户已设置密码，必须验证旧密码
    if user.password:
        if not old_password:
            raise ValueError("请输入原密码")
        if not verify_password(old_password, user.password):
            logger.warning(f"❌ 修改密码失败 | 用户: {user.username} | 原因: 原密码错误")
            raise ValueError("原密码错误")

    user.password = hash_password(new_password)
    db.commit()

    logger.info(f"🔑 修改密码成功 | 用户: {user.username} | 用户ID: {user.id}")
    return True


@service_exception_handler
def reset_user_password(db: Session, phone: str, new_password: str) -> bool:
    """
    通过手机号重置密码

    参数:
        db: 数据库会话
        phone: 手机号
        new_password: 新密码

    异常:
        ValueError: 用户不存在或密码不符合要求
    """
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise ValueError("该手机号未注册")

    user.password = hash_password(new_password)
    db.commit()

    logger.info(f"🔑 重置密码成功 | 手机号: {phone} | 用户ID: {user.id}")
    return True


@service_exception_handler
def login_by_code_service(db: Session, credential: str, code: str) -> dict:
    """
    统一验证码登录（自动识别手机号/邮箱，用户名不支持验证码）

    未注册的手机号/邮箱会自动创建账号。

    返回:
        dict: {"token", "role", "username", "avatar"}

    异常:
        ValueError: 验证码错误 / 用户名不支持验证码
    """
    from services.verify_code_service import check_sms_code, verify_code

    credential = credential.strip()

    # 手机号 → 短信验证码
    if re.match(r'^1[3-9]\d{9}$', credential):
        if not check_sms_code(credential, code):
            raise ValueError("验证码错误或已过期")
        user = db.query(User).filter(User.phone == credential).first()
        if not user:
            user = db_create_user(db, username=credential, password=None, role="user", phone=credential)
            logger.info(f"手机号自动注册: {credential}, 用户ID: {user.id}")
        elif not user.is_active:
            raise ValueError("该账号已被停用")
        return build_login_response(user, db=db)

    # 邮箱 → 邮箱验证码
    if '@' in credential:
        if not verify_code(credential, code):
            raise ValueError("验证码错误或已过期")
        user = db.query(User).filter(User.email == credential).first()
        if not user:
            user = db_create_user(db, username=credential, password=None, role="user", email=credential)
            logger.info(f"邮箱自动注册: {credential}, 用户ID: {user.id}")
        elif not user.is_active:
            raise ValueError("该账号已被停用")
        return build_login_response(user, db=db)

    # 用户名不支持验证码登录
    raise ValueError("用户名不支持验证码登录，请使用密码登录")


@service_exception_handler
def reset_user_password_service(db: Session, phone: str, code: str, new_password: str) -> bool:
    """
    通过手机号+验证码重置密码

    异常:
        ValueError: 手机号格式不正确、验证码错误、用户不存在
    """
    import re
    from services.verify_code_service import check_sms_code

    if not re.match(r'^1[3-9]\d{9}$', phone):
        raise ValueError("请输入正确的手机号")

    if not check_sms_code(phone, code):
        raise ValueError("验证码错误或已过期")

    return reset_user_password(db, phone, new_password)


@service_exception_handler
def upload_avatar_service(db: Session, user: User, file_contents: bytes, filename: str, content_type: str) -> str:
    """
    上传头像

    参数:
        db: 数据库会话
        user: 当前用户
        file_contents: 文件内容
        filename: 原始文件名
        content_type: MIME 类型

    返回:
        str: 头像 URL

    异常:
        ValueError: 文件类型不合法、文件过大
    """
    import os
    import uuid

    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if content_type not in allowed_types:
        raise ValueError("仅支持 JPG、PNG、GIF、WebP 格式的图片")

    if len(file_contents) > 1 * 1024 * 1024:
        raise ValueError("头像文件大小不能超过 1MB")

    # 删除旧头像文件
    if user.avatar:
        old_path = user.avatar.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = filename.split(".")[-1] if "." in filename else "jpg"
    new_filename = f"{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join("uploads", "avatars", new_filename)
    with open(filepath, "wb") as f:
        f.write(file_contents)

    avatar_url = f"/uploads/avatars/{new_filename}"
    update_avatar(db, user, avatar_url)

    return avatar_url


"""
管理员初始化
用于创建默认管理员账户
"""
def init_admin():
    """
    初始化默认管理员账户
    """
    if not AUTO_CREATE_ADMIN:
        logger.info("ℹ️  自动创建管理员功能已禁用")
        return

    db = SessionLocal()
    try:
        # 检查是否已存在管理员
        admin_exists = db.query(User).filter(User.role == "admin").first()

        if admin_exists:
            logger.info("✅ 管理员账户已存在")
            return

        # 复用 db_create_user 创建管理员
        admin_user = db_create_user(db, ADMIN_USERNAME, ADMIN_PASSWORD, role="admin")

        logger.info("=" * 50)
        logger.info("✅ 默认管理员账户创建成功！")
        logger.info(f"👤 用户名: {admin_user.username}")
        logger.info(f"🔑 密码: {ADMIN_PASSWORD}")
        logger.warning("⚠️  请在首次登录后立即修改密码！")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"❌ 创建管理员失败: {str(e)}")
        raise
    finally:
        db.close()


