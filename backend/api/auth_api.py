from fastapi import APIRouter, Depends, Request, UploadFile, File, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database.db import get_db
from schemas.user_schema import UserLogin, CodeLogin, UserCreate, PasswordChange, ProfileUpdate, ResetPassword
from services.admin_user_service import (
    login_user, change_user_password, get_user_profile, update_username,
    db_create_user, login_by_code_service,
    reset_user_password_service, upload_avatar_service,
    bind_phone, bind_email, unbind_phone, unbind_email,
)
from services.verify_code_service import send_verify_code_service
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success, error
from utils.auth import logout_token, get_current_user_obj, security
from utils.rate_limiter import login_limiter
from database.models.user import User
from services.permission_service import get_user_permission_codes, invalidate_user_perm_cache

router = APIRouter(tags=["认证管理"])


class SendCodeRequest(BaseModel):
    target: str = Field(..., description="手机号或邮箱")


class BindPhoneRequest(BaseModel):
    phone: str = Field(..., description="手机号")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")


class BindEmailRequest(BaseModel):
    email: str = Field(..., description="邮箱")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")


@router.post("/auth/login", summary="统一密码登录（手机号/邮箱/用户名）")
@handle_api_exception
def login(data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    login_limiter.check(client_ip)

    result = login_user(db, data.username, data.password)
    token = result.pop("token")
    response.headers["Authorization"] = f"Bearer {token}"
    return success(result, msg="登录成功")


@router.post("/auth/send-code", summary="发送验证码")
@handle_api_exception
def send_verify_code(data: SendCodeRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    login_limiter.check(client_ip)

    ok, msg = send_verify_code_service(data.target)
    if not ok:
        raise ValueError(msg)
    return success(msg=msg)


@router.post("/auth/login-code", summary="统一验证码登录（手机号/邮箱）")
@handle_api_exception
def login_by_code(data: CodeLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    login_limiter.check(client_ip)

    result = login_by_code_service(db, data.username, data.code)
    token = result.pop("token")
    response.headers["Authorization"] = f"Bearer {token}"
    return success(result, msg="登录成功")


@router.post("/auth/register", summary="用户注册", status_code=201)
@handle_api_exception
def register_new_user(data: UserCreate, db: Session = Depends(get_db)):
    user = db_create_user(db, data.username, data.password, role="user", action="注册")
    return success(data={"id": user.id, "username": user.username, "role": user.role}, msg="用户注册成功")


@router.post("/auth/logout", summary="退出登录")
@handle_api_exception
def logout(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.headers.get("X-Token")

    if not token:
        return error("未提供认证凭证", code=401)

    logout_token(token)
    return success(msg="退出成功，Token 已失效")


@router.put("/auth/password", summary="修改密码")
@handle_api_exception
def change_password(
        data: PasswordChange,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_obj)
):
    change_user_password(db, current_user, data.old_password, data.new_password)
    return success(msg="密码修改成功")


@router.post("/auth/reset-password", summary="忘记密码")
@handle_api_exception
def forgot_password(data: ResetPassword, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    login_limiter.check(client_ip)

    reset_user_password_service(db, data.phone, data.code, data.new_password)
    return success(msg="密码重置成功")


@router.get("/auth/profile", summary="获取个人信息")
@handle_api_exception
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj)
):
    return success(get_user_profile(current_user, db), msg="获取个人信息成功")


@router.get("/auth/permissions", summary="刷新当前用户的权限列表")
@handle_api_exception
def refresh_own_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj)
):
    """清除缓存并重新查询当前用户的权限，用于管理员修改权限后前端主动刷新"""
    invalidate_user_perm_cache(current_user.id)
    permissions = get_user_permission_codes(db, current_user.id, current_user.role)
    return success(data={"permissions": permissions}, msg="权限刷新成功")


@router.put("/auth/profile", summary="修改用户名")
@handle_api_exception
def update_profile(
        data: ProfileUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_obj)
):
    update_username(db, current_user, data.username)
    return success(msg="用户名修改成功")


@router.put("/auth/avatar", summary="上传头像")
@handle_api_exception
async def upload_avatar(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_obj)
):
    contents = await file.read()
    avatar_url = upload_avatar_service(db, current_user, contents, file.filename, file.content_type)
    return success({"avatar": avatar_url}, msg="头像上传成功")


@router.put("/auth/bind-phone", summary="绑定手机号")
@handle_api_exception
def bind_user_phone(
        data: BindPhoneRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_obj)
):
    bind_phone(db, current_user, data.phone, data.code)
    return success(msg="手机号绑定成功")


@router.put("/auth/bind-email", summary="绑定邮箱")
@handle_api_exception
def bind_user_email(
        data: BindEmailRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_obj)
):
    bind_email(db, current_user, data.email, data.code)
    return success(msg="邮箱绑定成功")


@router.delete("/auth/bind-phone", summary="解绑手机号")
@handle_api_exception
def unbind_user_phone(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_obj)
):
    unbind_phone(db, current_user)
    return success(msg="手机号解绑成功")


@router.delete("/auth/bind-email", summary="解绑邮箱")
@handle_api_exception
def unbind_user_email(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_obj)
):
    unbind_email(db, current_user)
    return success(msg="邮箱解绑成功")
