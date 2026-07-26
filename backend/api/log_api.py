from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from utils.auth import RequirePermission
from database.db import get_db
from services.log_service import query_logs, export_logs, _build_admin_log_msg, _build_my_log_msg
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

    return success(
        data={"total": total, "page": params.page, "size": params.size, "list": log_list},
        msg=_build_admin_log_msg(params, total, len(log_list))
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

    return success(
        data={"total": total, "page": params.page, "size": params.size, "list": log_list},
        msg=_build_my_log_msg(total, len(log_list))
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
