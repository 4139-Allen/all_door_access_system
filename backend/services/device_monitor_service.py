"""
设备状态监控服务
后台定时检测设备在线状态，通过 Redis key 过期判断设备离线
"""
import asyncio
from database.redis import redis_client
from database.db import SessionLocal
from database.models.device import Device
from services.websocket_service import manager as ws_manager
from utils.logger import AppLogger

logger = AppLogger.get_logger()

# mqtt_name -> db_id
_known_online: dict = {}
_task = None


def mark_device_online(db_id: int, mqtt_name: str):
    """标记设备为在线（由 MQTT 回调调用）"""
    _known_online[mqtt_name] = db_id


def is_device_known_online(mqtt_name: str) -> bool:
    """检查设备是否已在已知在线列表中（用于判断是否首次上线）"""
    return mqtt_name in _known_online


async def _monitor_loop():
    """每 25 秒检查一次已知在线设备的 Redis key 是否过期"""
    while True:
        await asyncio.sleep(25)
        expired = []
        for mqtt_name, db_id in list(_known_online.items()):
            if not redis_client or not redis_client.exists(f"device:online:{mqtt_name}"):
                expired.append((mqtt_name, db_id))

        for mqtt_name, db_id in expired:
            _known_online.pop(mqtt_name, None)
            db = SessionLocal()
            try:
                device = db.query(Device).filter(Device.id == db_id).first()
                if device:
                    device.status = "offline"
                    db.commit()
                    await ws_manager.send_device_status(
                        device_id=db_id,
                        device_name=device.name,
                        status="offline",
                        location=device.location or ""
                    )
                    logger.info(f"设备离线 [{device.name}]")
            except Exception as e:
                logger.warning(f"设备离线处理失败 [{mqtt_name}]: {e}")
            finally:
                db.close()


def start_device_monitor():
    """启动设备状态监控"""
    global _task
    loop = asyncio.get_event_loop()
    _task = loop.create_task(_monitor_loop())
    logger.info("设备状态监控已启动")


def stop_device_monitor():
    """停止设备状态监控"""
    global _task
    if _task:
        _task.cancel()
        _task = None
        logger.info("设备状态监控已停止")
