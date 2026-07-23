"""
权限管理服务
提供角色和权限的 CRUD、角色权限分配、用户权限查询等功能
"""
from sqlalchemy.orm import Session
from database.models.role import Role
from database.models.permission import Permission
from database.models.role_permission import RolePermission
from database.models.user import User
from database.redis import redis_client, cache_get_json, cache_set_json
from utils.service_exception_handler import service_exception_handler
from utils.logger import AppLogger
from core.exceptions import NotFoundError

logger = AppLogger.get_logger()

PERM_CACHE_KEY = "perm:user:{user_id}"
PERM_CACHE_TTL = 300  # 5 分钟


# ==========================================
# 权限查询
# ==========================================
def get_user_permission_codes(db: Session, user_id: int, role_code: str) -> list[str]:
    """
    获取用户的权限 code 列表（带 Redis 缓存）

    参数:
        db: 数据库会话
        user_id: 用户 ID（用于缓存 key）
        role_code: 角色标识（如 "admin"）

    返回:
        list[str]: 权限 code 列表
    """
    cache_key = PERM_CACHE_KEY.format(user_id=user_id)
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    permissions = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .filter(Role.code == role_code)
        .all()
    )
    codes = [p.code for p in permissions]

    cache_set_json(cache_key, codes, PERM_CACHE_TTL)
    return codes


def user_has_permission(db: Session, user: User, *codes: str) -> bool:
    """
    检查用户是否拥有指定权限中的任意一个（供 service 层调用）

    参数:
        db: 数据库会话
        user: User 对象
        *codes: 权限 code 列表（满足任意一个即返回 True）

    返回:
        bool
    """
    perm_codes = get_user_permission_codes(db, user.id, user.role)
    return any(c in perm_codes for c in codes)


def invalidate_user_perm_cache(user_id: int):
    """清除指定用户的权限缓存"""
    if redis_client:
        redis_client.delete(PERM_CACHE_KEY.format(user_id=user_id))


def invalidate_all_perm_cache():
    """清除所有用户的权限缓存（角色权限变更时调用）"""
    if redis_client:
        keys = list(redis_client.scan_iter("perm:user:*"))
        if keys:
            redis_client.delete(*keys)


# ==========================================
# 权限列表
# ==========================================
@service_exception_handler
def get_all_permissions(db: Session) -> list[dict]:
    """
    获取所有权限（按模块分组）

    返回:
        list[dict]: [{"module": "设备管理", "permissions": [{"id", "code", "name"}, ...]}, ...]
    """
    permissions = db.query(Permission).order_by(Permission.module, Permission.sort, Permission.id).all()

    module_map: dict[str, list] = {}
    for p in permissions:
        if p.module not in module_map:
            module_map[p.module] = []
        module_map[p.module].append({
            "id": p.id,
            "code": p.code,
            "name": p.name,
        })

    return [{"module": m, "permissions": ps} for m, ps in module_map.items()]


# ==========================================
# 角色 CRUD
# ==========================================
@service_exception_handler
def get_all_roles(db: Session) -> list[dict]:
    """
    获取所有角色（含权限列表）

    返回:
        list[dict]: [{"id", "name", "code", "is_system", "permissions": [{"id", "code", "name"}]}]
    """
    roles = db.query(Role).order_by(Role.id).all()
    result = []
    for r in roles:
        permissions = (
            db.query(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id == r.id)
            .order_by(Permission.module, Permission.sort, Permission.id)
            .all()
        )
        result.append({
            "id": r.id,
            "name": r.name,
            "code": r.code,
            "is_system": r.is_system,
            "permissions": [{"id": p.id, "code": p.code, "name": p.name, "module": p.module} for p in permissions],
        })
    return result


@service_exception_handler
def create_role(db: Session, name: str, code: str) -> Role:
    """
    创建自定义角色

    异常:
        ValueError: 角色名称或标识已存在
    """
    if db.query(Role).filter(Role.name == name).first():
        raise ValueError(f"角色名称 '{name}' 已存在")
    if db.query(Role).filter(Role.code == code).first():
        raise ValueError(f"角色标识 '{code}' 已存在")

    role = Role(name=name, code=code, is_system=False)
    db.add(role)
    db.commit()
    db.refresh(role)

    logger.info(f"✅ 创建角色成功 | 名称: {name} | 标识: {code}")
    return role


@service_exception_handler
def update_role(db: Session, role_id: int, name: str) -> Role:
    """
    修改角色名称

    异常:
        NotFoundError: 角色不存在
        ValueError: 名称已被其他角色使用
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise NotFoundError("角色不存在")

    existing = db.query(Role).filter(Role.name == name, Role.id != role_id).first()
    if existing:
        raise ValueError(f"角色名称 '{name}' 已被使用")

    role.name = name
    db.commit()
    db.refresh(role)

    logger.info(f"✅ 修改角色成功 | ID: {role_id} | 新名称: {name}")
    return role


@service_exception_handler
def delete_role(db: Session, role_id: int) -> bool:
    """
    删除自定义角色

    异常:
        NotFoundError: 角色不存在
        ValueError: 系统内置角色不可删除、角色下有用户时不可删除
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise NotFoundError("角色不存在")
    if role.is_system:
        raise ValueError("系统内置角色不可删除")

    # 检查是否有用户使用该角色
    user_count = db.query(User).filter(User.role == role.code).count()
    if user_count > 0:
        raise ValueError(f"该角色下有 {user_count} 个用户，请先迁移用户后再删除")

    db.delete(role)
    db.commit()
    invalidate_all_perm_cache()

    logger.info(f"🗑️  删除角色成功 | ID: {role_id} | 名称: {role.name}")
    return True


# ==========================================
# 角色权限分配
# ==========================================
@service_exception_handler
def set_role_permissions(db: Session, role_id: int, permission_ids: list[int]) -> dict:
    """
    设置角色的权限（全量替换）

    参数:
        db: 数据库会话
        role_id: 角色 ID
        permission_ids: 权限 ID 列表

    返回:
        dict: {"role_id", "role_name", "permission_count"}

    异常:
        NotFoundError: 角色不存在
        ValueError: 包含无效的权限 ID
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise NotFoundError("角色不存在")
    if role.code == "admin":
        raise ValueError("超级管理员角色的权限不可修改")

    # 验证所有 permission_id 是否合法
    if permission_ids:
        valid_ids = {p.id for p in db.query(Permission.id).filter(Permission.id.in_(permission_ids)).all()}
        invalid = set(permission_ids) - valid_ids
        if invalid:
            raise ValueError(f"无效的权限ID: {invalid}")

    # 删除旧的关联
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

    # 插入新的关联
    for pid in permission_ids:
        db.add(RolePermission(role_id=role_id, permission_id=pid))

    db.commit()
    invalidate_all_perm_cache()

    logger.info(f"✅ 设置角色权限成功 | 角色: {role.name} | 权限数: {len(permission_ids)}")
    return {
        "role_id": role_id,
        "role_name": role.name,
        "permission_count": len(permission_ids),
    }


# ==========================================
# 数据初始化（启动时调用）
# ==========================================
def init_permissions(db: Session):
    """
    初始化角色和权限数据（幂等，已存在则跳过）
    """
    # 1. 创建系统角色
    system_roles = [
        {"name": "超级管理员", "code": "admin"},
        {"name": "普通管理员", "code": "operator"},
        {"name": "普通用户", "code": "user"},
    ]
    for r in system_roles:
        if not db.query(Role).filter(Role.code == r["code"]).first():
            db.add(Role(name=r["name"], code=r["code"], is_system=True))
    db.commit()

    # 2. 创建权限
    perm_data = [
        # (code, name, module, sort)
        ("dashboard.view", "查看仪表盘", "仪表盘", 1),
        ("door.open", "远程开门", "门禁控制", 1),
        ("door.view_own_log", "查看个人开门记录", "门禁控制", 2),
        ("device.view", "查看设备列表", "设备管理", 1),
        ("device.create", "创建设备", "设备管理", 2),
        ("device.edit", "编辑设备", "设备管理", 3),
        ("device.delete", "删除设备", "设备管理", 4),
        ("device.bind", "绑定/解绑用户", "设备管理", 5),
        ("log.view", "查看全部开门记录", "日志管理", 1),
        ("log.export", "导出日志", "日志管理", 2),
        ("alert.view", "查看异常事件", "异常事件", 1),
        ("alert.unlock", "解除设备锁定", "异常事件", 2),
        ("user.view", "查看用户列表", "用户管理", 1),
        ("user.manage", "管理用户", "用户管理", 2),
    ]
    existing = {p.code: p for p in db.query(Permission).all()}
    for code, name, module, sort in perm_data:
        if code not in existing:
            db.add(Permission(code=code, name=name, module=module, sort=sort))
        else:
            # 同步已有权限的名称/模块（允许代码定义覆盖数据库）
            perm = existing[code]
            if perm.name != name or perm.module != module:
                perm.name = name
                perm.module = module
    db.commit()

    # 3. 分配默认权限
    role_perm_map = {
        "admin": [p[0] for p in perm_data],  # 全部权限
        "operator": [
            "dashboard.view", "door.open", "door.view_own_log",
            "device.view", "device.create", "device.edit", "device.delete", "device.bind",
            "log.view", "log.export",
            "alert.view", "alert.unlock",
        ],
        "user": ["dashboard.view", "door.open", "door.view_own_log"],
    }

    for role_code, perm_codes in role_perm_map.items():
        role = db.query(Role).filter(Role.code == role_code).first()
        if not role:
            continue

        # 获取角色当前已有的权限ID
        existing_perm_ids = {
            rp.permission_id for rp in
            db.query(RolePermission.permission_id).filter(RolePermission.role_id == role.id).all()
        }

        # 获取需要分配的权限
        perms = db.query(Permission).filter(Permission.code.in_(perm_codes)).all()

        # 只添加缺失的权限
        added = 0
        for p in perms:
            if p.id not in existing_perm_ids:
                db.add(RolePermission(role_id=role.id, permission_id=p.id))
                added += 1

        if added > 0:
            logger.info(f"为角色 [{role.name}] 新增 {added} 个权限")

    db.commit()
    logger.info("✅ 权限数据初始化完成")
