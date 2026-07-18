
from pydantic import BaseModel, Field, field_validator
import re

USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_一-龥]+$')


def _validate_password(v: str) -> str:
    """密码校验：去空格 + 长度检查"""
    v = v.strip()
    if not v:
        raise ValueError('密码不能为空')
    if len(v) < 6:
        raise ValueError('密码长度不能少于6个字符')
    if len(v) > 20:
        raise ValueError('密码长度不能超过20个字符')
    return v


def _validate_username(v: str) -> str:
    """通用用户名校验：去空格 + 格式 + 长度检查"""
    v = v.strip()
    if not v:
        raise ValueError('用户名不能为空')
    if len(v) > 30:
        raise ValueError('用户名长度不能超过30个字符')
    if not USERNAME_PATTERN.match(v):
        raise ValueError('用户名只能包含字母、数字、下划线和中文')
    return v


# 前端登录时 → 必须按这个格式传参
class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=30, description="用户名")
    password: str = Field(..., min_length=6, max_length=20, description="密码")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        return _validate_username(v)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return _validate_password(v)


# 前端注册时 → 必须按这个格式传参
class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=30, description="用户名")
    password: str = Field(..., min_length=6, max_length=20, description="密码")
    role: str = Field("user", description="角色: user, operator, admin")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        return _validate_username(v)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return _validate_password(v)

# 修改密码请求模型
class PasswordChange(BaseModel):
    old_password: str | None = Field(None, description="原密码（未设置密码时可为空）")
    new_password: str = Field(..., min_length=6, max_length=20, description="新密码")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        return _validate_password(v)


# 修改用户名请求模型
class ProfileUpdate(BaseModel):
    username: str = Field(..., min_length=1, max_length=30, description="新用户名")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        return _validate_username(v)


# 重置密码请求模型
class ResetPassword(BaseModel):
    phone: str = Field(..., description="手机号")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")
    new_password: str = Field(..., min_length=6, max_length=20, description="新密码")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        return _validate_password(v)


# 修改用户角色请求模型
class RoleUpdate(BaseModel):
    role: str = Field(..., min_length=1, max_length=30, description="角色标识")
