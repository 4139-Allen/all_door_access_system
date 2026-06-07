import asyncio
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from fastapi import WebSocket
from jose import jwt, JWTError

from core.config import SECRET_KEY, ALGORITHM
from database.db import SessionLocal
from database.models.user import User
from database.models.user_device import UserDevice
from database.redis import redis_client
from utils.logger import AppLogger
from services.permission_service import user_has_permission

logger = AppLogger.get_logger()
WS_AUTH_TIMEOUT = 10


def _build_door_msg(username: str, device_name: str, location: str, action: str, device_id: int) -> dict:
    """构建开门事件消息"""
    return {
        "type": "door_open",
        "message": f"【{username}】打开了【{device_name}】({location})",
        "username": username,
        "device_name": device_name,
        "location": location or "",
        "action": action,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device_id": device_id
    }


async def _safe_send(websocket: WebSocket, msg: dict) -> bool:
    """安全发送 WebSocket 消息，返回是否成功"""
    try:
        await websocket.send_json(msg)
        return True
    except Exception as e:
        logger.warning(f"WebSocket 推送失败: {e}")
        return False


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_info: Dict[int, dict] = {}

    async def connect(self, websocket: WebSocket, user_id: int, is_admin: bool):
        self.active_connections.append(websocket)
        self.user_info[id(websocket)] = {"websocket": websocket, "user_id": user_id, "is_admin": is_admin}

    def disconnect(self, websocket: WebSocket):
        self.user_info.pop(id(websocket), None)
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def _get_bound_user_ids(self, device_id: int) -> set:
        """获取绑定了指定设备的用户 ID 集合"""
        db = SessionLocal()
        try:
            bindings = db.query(UserDevice.user_id).filter(UserDevice.device_id == device_id).all()
            return {b.user_id for b in bindings}
        finally:
            db.close()

    async def send_door_event(self, device_id: int, username: str, device_name: str, location: str, action: str = "开门"):
        """向绑定了该设备的用户和所有管理员推送开门事件"""
        msg = _build_door_msg(username, device_name, location, action, device_id)
        bound_user_ids = self._get_bound_user_ids(device_id)

        for info in list(self.user_info.values()):
            if info["is_admin"] or info["user_id"] in bound_user_ids:
                await _safe_send(info["websocket"], msg)

    async def send_device_status(self, device_id: int, device_name: str, status: str, location: str = ""):
        """向所有在线用户推送设备状态变化"""
        msg = {"type": "device_status", "device_id": device_id, "device_name": device_name, "status": status, "location": location}
        for info in list(self.user_info.values()):
            await _safe_send(info["websocket"], msg)


manager = ConnectionManager()


async def _auth_fail(websocket: WebSocket, msg: str):
    """发送认证失败消息"""
    await websocket.send_json({"type": "auth", "status": "failed", "msg": msg})


async def authenticate_websocket(websocket: WebSocket) -> Optional[Tuple[int, bool]]:
    """WebSocket 认证，返回 (user_id, is_admin) 或 None"""
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=WS_AUTH_TIMEOUT)
        data = json.loads(raw)
    except (asyncio.TimeoutError, json.JSONDecodeError) as e:
        await _auth_fail(websocket, "认证超时或消息格式错误")
        return None

    if data.get("type") != "auth":
        await _auth_fail(websocket, "请先发送认证信息")
        return None

    token = data.get("token", "")
    if not token:
        await _auth_fail(websocket, "Token 不能为空")
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        await _auth_fail(websocket, "Token 无效")
        return None

    uid = payload.get("sub")
    if uid is None:
        await _auth_fail(websocket, "Token 无效")
        return None

    # 检查黑名单和 Redis 活跃 token
    if redis_client:
        if redis_client.exists(f"blacklist:{token}"):
            await _auth_fail(websocket, "Token 已注销")
            return None
        if not redis_client.exists(f"token:{token}"):
            await _auth_fail(websocket, "Token 已过期")
            return None

    user_id = int(uid)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        is_admin = user and user_has_permission(db, user, "log.view")
    finally:
        db.close()

    await websocket.send_json({"type": "auth", "status": "ok"})
    logger.info(f"WebSocket 认证成功: user_id={user_id}, is_admin={is_admin}")
    return user_id, is_admin
