from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

# 从统一配置模块导入
from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Redis
from database.redis import redis_client
from database.db import get_db
from database.models.user import User

security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ====================== 创建 token（存入 Redis）======================
def create_access_token(data: dict, expires_minutes: int = None) -> str:
    """
    创建 JWT Token 并存储到 Redis

    参数:
        data: 包含用户信息的字典，必须包含 'sub' 字段
        expires_minutes: 自定义过期时间（分钟），默认使用配置值

    返回:
        str: JWT Token
    """
    sub = data.get("sub")
    if not sub or sub.strip() == "":
        raise ValueError("创建Token失败：'sub' 不能为空")

    minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode.update({"exp": expire})

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # 存入 Redis：key=token, value=user_id, 过期时间同步
    if redis_client:
        redis_client.setex(
            f"token:{token}",
            minutes * 60,
            sub
        )

    return token


def build_login_response(user, **extra) -> dict:
    """
    构建登录响应（token + 用户信息 + 权限列表）

    参数:
        user: User 对象
        **extra: 额外字段（如 has_password=True）

    返回:
        dict: {"token", "role", "username", "avatar", "permissions", ...extra}
    """
    token = create_access_token({"sub": str(user.id)})

    # 查询用户权限列表和角色名称
    from services.permission_service import get_user_permission_codes
    from database.models.role import Role
    from database.db import SessionLocal
    db = SessionLocal()
    try:
        permissions = get_user_permission_codes(db, user.id, user.role)
        role_obj = db.query(Role.name).filter(Role.code == user.role).first()
        role_name = role_obj.name if role_obj else user.role
    finally:
        db.close()

    data = {
        "token": token,
        "user_id": user.id,
        "role": user.role,
        "role_name": role_name,
        "username": user.username,
        "avatar": user.avatar,
        "permissions": permissions,
    }
    data.update(extra)
    return data


# ====================== 校验用户（先查 Redis + 黑名单）======================
def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    # 支持两种 token 传递方式：Authorization header（Web端）和 X-Token header（小程序端）
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.headers.get("X-Token")

    if not token:
        raise HTTPException(status_code=401, detail="未提供认证凭证")

    # ====================== 解码 JWT，自动校验过期======================
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token 无效")
    except JWTError:
        # 自动捕获：过期、伪造、无效
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    # ====================== 校验黑名单 ======================
    if redis_client and redis_client.exists(f"blacklist:{token}"):
        raise HTTPException(status_code=401, detail="Token 已注销，请重新登录")

    # ====================== 校验 Redis 是否存在 ======================
    if redis_client and not redis_client.exists(f"token:{token}"):
        raise HTTPException(status_code=401, detail="Token 已退出登录")

    return int(user_id)

# ====================== 退出登录（删除缓存 + 加入黑名单）======================
def logout_token(token: str):
    if redis_client:
        # 删除原来的登录缓存
        redis_client.delete(f"token:{token}")
        # 加入黑名单，过期时间和JWT一致（24小时足够）
        redis_client.setex(f"blacklist:{token}", 86400, "true")

# ====================== 获取当前用户对象 ======================
def get_current_user_obj(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    """获取当前用户对象，避免在各处重复查询"""
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

# ====================== 密码相关======================
def hash_password(password: str) -> str:
    """
    哈希密码

    参数:
        password: 明文密码

    返回:
        str: 哈希后的密码

    异常:
        ValueError: 密码超过72字节
    """
    if len(password.encode('utf-8')) > 72:
        raise ValueError("密码过长")
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    验证密码

    参数:
        plain: 明文密码
        hashed: 哈希后的密码

    返回:
        bool: 密码是否匹配
    """
    if len(plain.encode('utf-8')) > 72:
        return False
    return pwd_context.verify(plain, hashed)




# 基于权限的验证
def require_permission(*codes: str):
    """
    权限验证依赖工厂

    使用示例:
        @router.get("/devices")
        def list_devices(current_user: User = Depends(require_permission("device.view"))):
            ...

        @router.delete("/devices/{id}")
        def delete_device(current_user: User = Depends(require_permission("device.delete"))):
            ...
    """
    def dependency(current_user: User = Depends(get_current_user_obj)) -> User:
        from services.permission_service import get_user_permission_codes
        from database.db import SessionLocal

        db = SessionLocal()
        try:
            user_permissions = get_user_permission_codes(db, current_user.id, current_user.role)
        finally:
            db.close()

        if not any(code in user_permissions for code in codes):
            raise HTTPException(status_code=403, detail="无操作权限")
        return current_user

    return dependency

