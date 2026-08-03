"""
异常事件 API 路由
轻薄 API 层，仅负责接收请求和返回响应
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from utils.auth import RequirePermission
from database.db import get_db
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success
from database.models.user import User
from schemas.alert_schema import AlertListQuery
from services.alert_service import get_alert_list, get_alert_stats, unlock_device

router = APIRouter(tags=["异常事件"])


@router.get("/alerts", summary="获取异常事件列表")
@handle_api_exception
def get_alerts(
    params: AlertListQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("alert.view"))
):
    """获取异常事件列表（设备锁定、开门失败等）"""
    total, result = get_alert_list(
        db=db,
        current_user=current_user,
        page=params.page,
        size=params.size,
        device_name=params.device_name,
        alert_type=params.alert_type,
        start_time=params.start_time,
        end_time=params.end_time
    )

    if total == 0:
        msg = "没有异常事件记录" if not params.device_name and not params.alert_type else "没有找到符合条件的异常事件"
    else:
        msg = f"获取异常事件列表成功，共 {total} 条"

    return success(data={"total": total, "page": params.page, "size": params.size, "list": result}, msg=msg)


@router.get("/alerts/stats", summary="获取异常事件统计")
@handle_api_exception
def get_alert_stats_api(
    hours: int = Query(24, ge=1, le=720, description="统计时间范围（小时）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("alert.view"))
):
    """获取异常事件统计数据"""
    result = get_alert_stats(db=db, hours=hours)
    return success(data=result, msg="获取异常事件统计成功")


@router.post("/alerts/unlock/{device_name}", summary="解除设备锁定")
@handle_api_exception
def unlock_device_api(
    device_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("alert.unlock"))
):
    """解除设备密码锁定"""
    msg = unlock_device(db=db, device_name=device_name)
    return success(msg=msg)