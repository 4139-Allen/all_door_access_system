from fastapi import APIRouter, Depends, Path, Body, Query
from sqlalchemy.orm import Session
from database.db import get_db
from utils.auth import get_current_user_obj, require_permission
from utils.api_exception_handler import handle_api_exception
from core.response_schema import ApiResponse, success
from schemas.device_schema import DeviceCreate, DeviceUpdate, BindUserDevice
from services.device_service import (
    create_device,
    update_device,
    delete_device,
    bind_user_device,
    unbind_user_device,
    get_device_list,
)
from database.models.user import User
from typing import Optional

router = APIRouter(tags=["【超级管理员】设备管理"])


# 创建设备
@router.post("/devices", summary="新增设备", description="添加一个新的门禁设备", response_model=ApiResponse)
@handle_api_exception
def create(
        data: DeviceCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("device.create"))
):
    device = create_device(db, data)
    return success(data={"device_id": device.id}, msg="创建设备成功")


# 获取设备列表（所有登录用户可用，service 层根据权限过滤：有 device.view 看全部，否则只看绑定的）
@router.get("/devices", summary="获取设备列表", response_model=ApiResponse)
@handle_api_exception
def get_device_list_endpoint(
    page: int = Query(1, description="页码"),
    size: int = Query(10, description="每页条数"),
    name: Optional[str] = Query(None, description="设备名称模糊搜索"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj)
):
    device_data = get_device_list(
        db=db,
        current_user_id=current_user.id,
        role=current_user.role,
        name=name,
        page=page,
        size=size,
        current_user=current_user
    )
    return success(data=device_data)


# 更新设备
@router.put("/devices/{device_id}", summary="更新设备", description="修改设备名称/状态等信息", response_model=ApiResponse)
@handle_api_exception
def update(
        device_id: int = Path(...),
        data: DeviceUpdate = Body(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("device.edit"))
):
    update_device(db, device_id, data)
    return success(msg="更新成功")


# 删除设备
@router.delete("/devices/{device_id}", summary="删除设备", response_model=ApiResponse)
@handle_api_exception
def delete_device_endpoint(
        device_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("device.delete"))
):
    delete_device(db, device_id)
    return success(msg="删除设备成功")


# 绑定设备
@router.post("/devices/{device_id}/bind", summary="绑定用户到设备", response_model=ApiResponse)
@handle_api_exception
def admin_bind_device(
        device_id: int = Path(..., description="设备ID"),
        data: BindUserDevice = Body(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("device.bind"))
):
    bind_user_device(db, data.user_id, device_id, operator_id=current_user.id)
    return success(msg="绑定成功")


# 解绑设备
@router.delete("/devices/{device_id}/unbind", summary="解除用户与设备的绑定", response_model=ApiResponse)
@handle_api_exception
def unbind_user_device_endpoint(
        device_id: int = Path(..., description="设备ID"),
        user_id: int = Query(..., description="用户ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("device.bind"))
):
    unbind_user_device(db, user_id, device_id, operator_id=current_user.id)
    return success(msg="解除绑定成功")
