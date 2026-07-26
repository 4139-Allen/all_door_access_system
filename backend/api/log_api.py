from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from utils.auth import RequirePermission
from database.db import get_db
from services.door_service import query_logs, export_logs
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success
from database.models.user import User
from schemas.door_schema import LogQuery, LogExportQuery

router = APIRouter(tags=["日志管理"])


@router.get("/door-logs", summary="获取开门日志（管理员查看全部）")
@handle_api_exception
def get_logs(
    params: LogQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("log.view"))
):
    total, log_list = query_logs(
        db=db,
        params=params,
        current_user_id=current_user.id,
        can_view_all=True
    )

    # 根据筛选条件生成对应的消息
    filters = []
    if params.username:
        filters.append("指定用户名")
    if params.device_name:
        filters.append("指定设备")
    if params.status:
        filters.append(f"状态「{params.status}」")
    if params.start_time and params.end_time:
        filters.append(f"时间范围")
    elif params.start_time:
        filters.append("开始时间")
    elif params.end_time:
        filters.append("结束时间")

    if total == 0:
        if not filters:
            msg = "日志记录为空"
        else:
            msg = f"已筛选{'、'.join(filters)}，没有找到符合条件的记录"
    elif len(log_list) == 0:
        msg = f"当前页无数据，共 {total} 条记录"
    elif not filters:
        msg = f"获取日志成功，共 {total} 条"
    else:
        msg = f"已筛选{'、'.join(filters)}，共 {total} 条"

    return success(
        data={"total": total, "page": params.page, "size": params.size, "list": log_list},
        msg=msg
    )


@router.get("/door/my-logs", summary="获取个人开门日志（普通用户）")
@handle_api_exception
def get_my_logs(
    params: LogQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("door.view_own_log"))
):
    total, log_list = query_logs(
        db=db,
        params=params,
        current_user_id=current_user.id,
        can_view_all=False
    )

    if total == 0:
        msg = "暂无开门记录"
    elif len(log_list) == 0:
        msg = f"当前页无数据，共 {total} 条记录"
    else:
        msg = f"获取日志成功，共 {total} 条"

    return success(
        data={"total": total, "page": params.page, "size": params.size, "list": log_list},
        msg=msg
    )


@router.get("/door-logs/export", summary="导出门禁日志（Excel）")
@handle_api_exception
def export_logs_endpoint(
    params: LogExportQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("log.export"))
):
    log_list = export_logs(
        db=db,
        params=params,
        current_user_id=current_user.id,
        can_view_all=True
    )

    return success(
        data={"list": log_list},
        msg=f"导出 {len(log_list)} 条记录"
    )
