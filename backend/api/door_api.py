from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session

from utils.auth import RequirePermission
from database.db import get_db
from services.door_service import open_door_service
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success
from database.models.user import User
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

    return success(data={
        "device_id": result["device_id"],
        "device_name": result["device_name"],
        "location": result.get("location", ""),
        "username": result.get("username", ""),
        "time": result.get("time", ""),
        "success": result["success"],
    }, msg=result["message"])
