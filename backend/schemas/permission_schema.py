from pydantic import BaseModel, Field
from typing import Optional


class RoleCreate(BaseModel):
    """创建角色"""
    name: str = Field(..., min_length=1, max_length=30, description="角色名称")
    role_code: str = Field(..., min_length=1, max_length=30, description="角色标识")


class RoleUpdate(BaseModel):
    """修改角色名称"""
    name: str = Field(..., min_length=1, max_length=30, description="角色名称")


class RolePermissionUpdate(BaseModel):
    """设置角色权限（全量替换）"""
    permission_ids: list[int] = Field(..., description="权限ID列表")
