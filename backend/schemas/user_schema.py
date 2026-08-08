
from pydantic import BaseModel, Field, field_validator
import re

# 用户名字符规则：字母、数字、下划线、点、中划线
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.\-一-龥]+$')
# 手机号格式：中国大陆 11 位手机号
PHONE_PATTERN = re.compile(r'^1[3-9]\d{9}$')
# 邮箱格式：宽松校验（本地部分可含 +、% 等，域名须含点）
EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


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
    if len(v) > 32:
        raise ValueError('用户名长度不能超过32个字符')
    if not USERNAME_PATTERN.match(v):
        raise ValueError('用户名只能包含字母、数字、下划线、点和中划线')
    return v


def _validate_credential(v: str, is_code_login: bool = False) -> str:
    """
    登录凭据校验（手机号/邮箱/用户名），按类型给出针对性提示

    只校验「格式是否正确」，不校验账号是否存在——
    格式合法但账号不存在的输入放行到业务层，由服务返回「用户不存在/密码错误」。

    参数:
        v:             登录输入
        is_code_login: 是否验证码登录（该场景用户名不支持，交给业务层提示）
    """
    v = v.strip()
    if not v:
        raise ValueError('请输入手机号/邮箱/用户名')
    # 手机号
    if PHONE_PATTERN.match(v):
        return v
    # 邮箱
    if '@' in v:
        if not EMAIL_PATTERN.match(v):
            raise ValueError('邮箱格式不正确，请检查输入')
        return v
    # 看起来像手机号（含数字、无字母/中文）但格式不对 → 针对性提示
    if re.search(r'\d', v) and not re.search(r'[a-zA-Z一-龥@]', v):
        raise ValueError('手机号格式不正确，请输入正确的11位手机号')
    # 验证码登录不支持用户名
    if is_code_login:
        raise ValueError('用户名不支持验证码登录，请使用密码登录')
    # 用户名
    if not USERNAME_PATTERN.match(v):
        raise ValueError('用户名只能包含字母、数字、下划线、点和中划线')
    return v


# 统一密码登录（自动识别手机号/邮箱/用户名）
class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=32, description="手机号/邮箱/用户名")
    password: str = Field(..., description="密码")

    @field_validator('username')
    @classmethod
    def validate_credential(cls, v):
        return _validate_credential(v)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return _validate_password(v)


# 统一验证码登录（自动识别手机号/邮箱，用户名不支持验证码）
class CodeLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=32, description="手机号/邮箱")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")

    @field_validator('username')
    @classmethod
    def validate_credential(cls, v):
        return _validate_credential(v, is_code_login=True)


# 前端注册时 → 必须按这个格式传参
class UserCreate(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
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
    new_password: str = Field(..., description="新密码")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        return _validate_password(v)


# 修改用户名请求模型
class ProfileUpdate(BaseModel):
    username: str = Field(..., description="新用户名")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        return _validate_username(v)


# 重置密码请求模型
class ResetPassword(BaseModel):
    phone: str = Field(..., description="手机号")
    code: str = Field(..., min_length=4, max_length=8, description="验证码")
    new_password: str = Field(..., description="新密码")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        return _validate_password(v)


# 修改用户角色请求模型
class RoleUpdate(BaseModel):
    role: str = Field(..., min_length=1, max_length=30, description="角色标识")
