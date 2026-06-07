from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db import get_db
from utils.auth import get_current_user_obj
from utils.api_exception_handler import handle_api_exception
from core.response_schema import ApiResponse, success
from database.models.user import User
from services.stat_service import get_statistics, get_weekly_trend, get_action_distribution

router = APIRouter(tags=["统计数据"])


@router.get("/statistics", summary="获取统计数据", response_model=ApiResponse)
@handle_api_exception
def get_stat(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj)
):
    data = get_statistics(db, current_user)
    return success(data=data)


@router.get("/statistics/trend", summary="本周开锁趋势", response_model=ApiResponse)
@handle_api_exception
def get_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj)
):
    data = get_weekly_trend(db, current_user)
    return success(data=data)


@router.get("/statistics/actions", summary="开锁方式占比", response_model=ApiResponse)
@handle_api_exception
def get_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj)
):
    data = get_action_distribution(db, current_user)
    return success(data=data)
