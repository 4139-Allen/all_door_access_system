from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from utils.auth import RequirePermission
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success
from database.models.user import User
from services.stat_service import get_statistics, get_weekly_trend, get_action_distribution

router = APIRouter(tags=["统计数据"])


@router.get("/statistics", summary="获取统计数据")
@handle_api_exception
def get_stat(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("dashboard.view"))
):
    data = get_statistics(db, current_user)
    return success(data=data, msg="获取统计数据成功")


@router.get("/statistics/trend", summary="本周开锁趋势")
@handle_api_exception
def get_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("dashboard.view"))
):
    data = get_weekly_trend(db, current_user)
    return success(data=data, msg="获取趋势数据成功")


@router.get("/statistics/actions", summary="开锁方式占比")
@handle_api_exception
def get_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequirePermission("dashboard.view"))
):
    data = get_action_distribution(db, current_user)
    return success(data=data, msg="获取开锁方式数据成功")
