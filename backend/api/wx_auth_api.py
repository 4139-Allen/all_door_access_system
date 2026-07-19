from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database.db import get_db
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success
from utils.auth import get_current_user
from services.wx_auth_service import wx_login_service, wx_bind_service

router = APIRouter(tags=["微信小程序认证"])


class WxLoginRequest(BaseModel):
    code: str = Field(..., description="wx.login() 获取的临时登录凭证")


class WxBindRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")


@router.post("/auth/wx-login", summary="微信小程序登录")
@handle_api_exception
def wx_login(data: WxLoginRequest, response: Response, db: Session = Depends(get_db)):
    result = wx_login_service(db, data.code)
    token = result.pop("token")
    response.headers["Authorization"] = f"Bearer {token}"
    return success(result, msg="登录成功")


@router.put("/auth/wx-bind", summary="绑定已有账号到微信")
@handle_api_exception
def wx_bind(
    data: WxBindRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user)
):
    result = wx_bind_service(db, current_user_id, data.username, data.password)
    token = result.pop("token")
    response.headers["Authorization"] = f"Bearer {token}"
    return success(result, msg="绑定成功")
