from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from database.models.user import User
from schemas.permission_schema import RoleCreate, RoleUpdate, RolePermissionUpdate
from services.permission_service import (
    get_all_permissions,
    get_all_roles,
    create_role,
    update_role,
    delete_role,
    set_role_permissions,
)
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success
from utils.auth import RequirePermission

router = APIRouter(tags=["权限管理"])


@router.get("/permissions", summary="获取所有权限（按模块分组）")
@handle_api_exception
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("user.manage")),
):
    data = get_all_permissions(db)
    return success(data, msg="获取权限列表成功")


@router.get("/roles", summary="获取所有角色及权限")
@handle_api_exception
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("user.manage")),
):
    data = get_all_roles(db)
    return success(data, msg="获取角色列表成功")


@router.post("/roles", summary="创建自定义角色", status_code=201)
@handle_api_exception
def add_role(
    body: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("user.manage")),
):
    role = create_role(db, body.name, body.code)
    return success({"id": role.id, "name": role.name, "role_code": role.role_code}, msg="创建成功")


@router.put("/roles/{role_id}", summary="修改角色名称")
@handle_api_exception
def edit_role(
    role_id: int,
    body: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("user.manage")),
):
    update_role(db, role_id, body.name)
    return success(msg="修改成功")


@router.delete("/roles/{role_id}", summary="删除自定义角色")
@handle_api_exception
def remove_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("user.manage")),
):
    delete_role(db, role_id)
    return success(msg="删除成功")


@router.put("/roles/{role_id}/permissions", summary="设置角色权限")
@handle_api_exception
def update_role_permissions(
    role_id: int,
    body: RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("user.manage")),
):
    result = set_role_permissions(db, role_id, body.permission_ids)
    return success(result, msg="权限设置成功")
