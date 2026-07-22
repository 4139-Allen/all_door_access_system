from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from database.db import get_db
from database.models.user import User
from schemas.user_schema import UserCreate, RoleUpdate
from services.admin_user_service import (
    db_create_user, delete_user_by_id, get_user_devices,
    get_users_list_formatted, import_users_from_bytes, update_user_role,
)
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success
from utils.auth import require_permission
from typing import Optional

router = APIRouter(tags=["【超级管理员】用户管理"])


@router.get("/users", summary="获取用户列表")
@handle_api_exception
def list_users(
        page: int = Query(1, ge=1),
        size: int = Query(10, ge=1),
        username: Optional[str] = Query(None, description="用户名模糊搜索"),
        role: Optional[str] = Query(None, description="角色筛选: admin/operator/user"),
        show_inactive: bool = Query(False, description="是否显示已停用用户"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("user.view"))
):
    data = get_users_list_formatted(db, page, size, username, role, show_inactive=show_inactive)
    return success(data, msg="获取用户列表成功")


@router.post("/users", summary="创建用户", status_code=201)
@handle_api_exception
def create_new_user(
        data: UserCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("user.manage"))
):
    user = db_create_user(db, data.username, data.password, role=data.role)
    return success(data={"id": user.id, "username": user.username, "role": user.role}, msg="用户创建成功")


@router.put("/users/{user_id}/role", summary="修改用户角色")
@handle_api_exception
def change_user_role(
        user_id: int,
        data: RoleUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("user.manage"))
):
    result = update_user_role(db, user_id, data.role, current_user)
    return success(result, msg="角色修改成功")


# 必须在 /users/{user_id} 之前定义，否则会被路径参数匹配
@router.post("/users/import", summary="批量导入用户", status_code=201)
@handle_api_exception
async def import_users(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("user.manage"))
):
    contents = await file.read()
    result = import_users_from_bytes(db, contents, file.filename)
    return success(result, msg=result["msg"])


@router.delete("/users/{user_id}", summary="删除用户")
@handle_api_exception
def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("user.manage"))
):
    delete_user_by_id(db, user_id, current_user)
    return success(msg="删除成功")


@router.get("/users/{user_id}/devices", summary="查询用户绑定的设备")
@handle_api_exception
def get_user_devices_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user.view"))
):
    device_list = get_user_devices(db, user_id)
    return success(data=device_list, msg="获取用户设备成功")
