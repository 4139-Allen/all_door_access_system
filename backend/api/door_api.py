from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session

from utils.auth import get_current_user_obj, RequirePermission
from database.db import get_db
from services.door_service import open_door_service, query_logs
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success
from database.models.user import User
from schemas.door_schema import LogQuery
from services.websocket_service import manager

router = APIRouter(tags=["门禁管理"])


@router.post("/doors/{device_id}/open", summary="开启门禁")
@handle_api_exception
async def door_open(
    device_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("door.open"))
):
    client_ip = request.client.host if request.client else None
    result = await open_door_service(
        db, current_user.id, device_id, ip=client_ip
    )

    background_tasks.add_task(
        manager.send_door_event,
        device_id=result["device_id"],
        username=result["username"],
        device_name=result["device_name"],
        location=result["location"],
        action="远程开门"
    )

    return success(msg=result["message"])


@router.get("/door-logs", summary="获取开门日志")
@handle_api_exception
def get_logs(
    params: LogQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("door.view_own_log"))
):
    total, log_list = query_logs(
        db=db,
        params=params,
        current_user_id=current_user.id
    )

    # 根据筛选条件生成对应的消息
    filters = []
    if params.user_id:
        filters.append("指定用户")
    if params.device_name:
        filters.append(f"设备「{params.device_name}」")
    if params.status:
        filters.append(f"状态「{params.status}」")
    if params.start_time and params.end_time:
        filters.append(f"时间范围")
    elif params.start_time:
        filters.append("开始时间")
    elif params.end_time:
        filters.append("结束时间")
    if not filters:
        msg = f"获取日志成功，共 {total} 条"
    else:
        msg = f"已筛选{'、'.join(filters)}，共 {total} 条"

    return success(
        data={"total": total, "list": log_list},
        msg=msg
    )
