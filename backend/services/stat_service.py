from sqlalchemy.orm import Session
from database.models.user import User
from database.models.device import Device
from database.models.door_log import DoorLog
from database.models.user_device import UserDevice
from datetime import datetime, date, timedelta
from utils.service_exception_handler import service_exception_handler
from typing import TypedDict
from database.redis import redis_client, cache_get_json, cache_set_json
from services.permission_service import user_has_permission
from utils.logger import AppLogger

logger = AppLogger.get_logger()

STAT_CACHE_KEY_TEMPLATE = "stat:user:{user_id}"
TREND_CACHE_KEY_TEMPLATE = "stat:trend:user:{user_id}"
ACTIONS_CACHE_KEY_TEMPLATE = "stat:actions:user:{user_id}"
STAT_CACHE_TTL = 180  # 秒


def invalidate_stat_cache(user_id: int):
    """清除指定用户的统计缓存（含趋势和开锁方式）"""
    if redis_client:
        try:
            redis_client.delete(
                STAT_CACHE_KEY_TEMPLATE.format(user_id=user_id),
                TREND_CACHE_KEY_TEMPLATE.format(user_id=user_id),
                ACTIONS_CACHE_KEY_TEMPLATE.format(user_id=user_id),
            )
        except Exception as e:
            logger.warning(f"清除用户统计缓存失败 [{user_id}]: {e}")


def invalidate_all_stat_cache():
    """清除所有用户的统计缓存"""
    if not redis_client:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match="stat:*", count=100)
            if keys:
                redis_client.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        logger.warning(f"清除全部统计缓存失败: {e}")


class StatisticsResult(TypedDict):
    user_total: int
    device_total: int
    today_log: int


def get_today_start() -> datetime:
    """获取今天开始时间"""
    return datetime.combine(date.today(), datetime.min.time())


@service_exception_handler
def get_statistics(db: Session, user: User) -> StatisticsResult:
    """获取统计数据（带缓存，180秒过期）"""
    cache_key = STAT_CACHE_KEY_TEMPLATE.format(user_id=user.id)
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    today_start = get_today_start()

    if user_has_permission(db, user, "log.view"):
        user_total = db.query(User).count()
        device_online = db.query(Device).filter(Device.status == "online").count()
        device_offline = db.query(Device).filter(Device.status != "online").count()
        today_log = db.query(DoorLog).filter(
            DoorLog.time >= today_start
        ).count()
    else:
        user_total = 1
        user_devices = db.query(UserDevice).filter(UserDevice.user_id == user.id).all()
        device_ids = [d.device_id for d in user_devices]
        device_online = db.query(Device).filter(Device.id.in_(device_ids), Device.status == "online").count() if device_ids else 0
        device_offline = db.query(Device).filter(Device.id.in_(device_ids), Device.status != "online").count() if device_ids else 0
        today_log = db.query(DoorLog).filter(
            DoorLog.user_id == user.id,
            DoorLog.time >= today_start
        ).count()

    data = {
        "user_total": user_total,
        "device_online": device_online,
        "device_offline": device_offline,
        "today_log": today_log
    }

    cache_set_json(cache_key, data, 180)
    return data


@service_exception_handler
def get_weekly_trend(db: Session, user: User) -> list:
    """获取近7天每天的开锁次数（滚动窗口，带缓存）"""
    cache_key = TREND_CACHE_KEY_TEMPLATE.format(user_id=user.id)
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    from sqlalchemy import func

    today = date.today()
    start = today - timedelta(days=6)
    start_dt = datetime.combine(start, datetime.min.time())

    query = db.query(
        func.date(DoorLog.time).label('day'),
        func.count().label('count')
    ).filter(DoorLog.time >= start_dt)

    if not user_has_permission(db, user, "log.view"):
        query = query.filter(DoorLog.user_id == user.id)

    rows = query.group_by(func.date(DoorLog.time)).all()

    day_map = {str(r.day): r.count for r in rows}
    result = []
    for i in range(7):
        d = start + timedelta(days=i)
        result.append({
            "day": d.strftime("%m/%d"),
            "count": day_map.get(str(d), 0)
        })

    cache_set_json(cache_key, result, STAT_CACHE_TTL)
    return result


@service_exception_handler
def get_action_distribution(db: Session, user: User) -> list:
    """获取开锁方式占比（带缓存）"""
    cache_key = ACTIONS_CACHE_KEY_TEMPLATE.format(user_id=user.id)
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    from sqlalchemy import func

    query = db.query(
        DoorLog.action,
        func.count().label('count')
    )

    if not user_has_permission(db, user, "log.view"):
        query = query.filter(DoorLog.user_id == user.id)

    rows = query.group_by(DoorLog.action).all()

    name_map = {
        '远程开门': '远程',
        '密码开门': '密码',
        '指纹开门': '指纹',
        '刷卡开门': 'RFID',
    }

    result = [
        {"name": name_map.get(r.action, r.action), "value": r.count}
        for r in rows
    ]

    cache_set_json(cache_key, result, STAT_CACHE_TTL)
    return result
