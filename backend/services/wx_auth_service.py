import secrets
import httpx
from sqlalchemy.orm import Session

from database.models.user import User
from core.config import WX_APPID, WX_SECRET
from utils.auth import create_access_token, verify_password, hash_password, build_login_response
from utils.service_exception_handler import service_exception_handler
from utils.logger import AppLogger

logger = AppLogger.get_logger()


def wx_code2session(code: str) -> dict:
    """用 code 换取 openid 和 session_key"""
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": WX_APPID,
        "secret": WX_SECRET,
        "js_code": code,
        "grant_type": "authorization_code"
    }
    with httpx.Client(timeout=10) as client:
        resp = client.get(url, params=params)
        data = resp.json()

    if "errcode" in data and data["errcode"] != 0:
        logger.warning(f"微信 code2session 失败 | errcode: {data.get('errcode')} | errmsg: {data.get('errmsg')}")
        raise ValueError(f"微信登录失败：{data.get('errmsg', 'code 无效')}")

    return data


@service_exception_handler
def wx_get_or_create_user(db: Session, openid: str) -> User:
    """根据 openid 查找或创建用户"""
    user = db.query(User).filter(User.openid == openid).first()
    if user:
        return user

    # 新用户：用 openid 前8位作为用户名，生成随机密码
    base_username = openid[:8]
    username = base_username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    random_password = secrets.token_urlsafe(16)
    user = User(
        username=username,
        password=hash_password(random_password),
        role="user",
        openid=openid
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"微信小程序新用户注册 | 用户名: {username} | 用户ID: {user.id}")
    return user


@service_exception_handler
def wx_login_service(db: Session, code: str) -> dict:
    """
    微信小程序登录完整流程

    返回:
        dict: {"token", "role", "username", "has_password"}

    异常:
        ValueError: 配置缺失或微信 API 调用失败
    """
    if not WX_APPID or not WX_SECRET:
        raise ValueError("微信登录未配置，请联系超级管理员")

    wechat_data = wx_code2session(code)
    openid = wechat_data["openid"]

    user = wx_get_or_create_user(db, openid)

    logger.info(f"微信小程序登录成功 | 用户ID: {user.id} | 用户名: {user.username}")

    return build_login_response(user, has_password=user.password is not None and len(user.password) > 0)


@service_exception_handler
def wx_bind_service(db: Session, current_user_id: int, username: str, password: str) -> dict:
    """
    将已有账号绑定到当前微信登录的用户

    返回:
        dict: {"token", "role", "username"}

    异常:
        ValueError: 用户不存在、密码错误、已绑定其他微信
    """
    wx_user = db.query(User).filter(User.id == current_user_id).first()
    if not wx_user:
        raise ValueError("用户不存在")

    target_user = db.query(User).filter(User.username == username).first()
    if not target_user:
        raise ValueError("用户名不存在")

    if not verify_password(password, target_user.password):
        raise ValueError("密码错误")

    if target_user.openid and target_user.openid != wx_user.openid:
        raise ValueError("该账号已绑定其他微信")

    target_user.openid = wx_user.openid
    db.delete(wx_user)
    db.commit()

    logger.info(f"微信绑定账号成功 | 微信用户ID: {current_user_id} -> 账号: {target_user.username}")

    return build_login_response(target_user)
