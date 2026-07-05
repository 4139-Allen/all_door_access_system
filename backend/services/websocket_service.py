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



def _build_door_msg(username: str, device_name: str, location: str, action: str, device_id: int, status: str = "成功") -> dict:
    """构建开门事件消息"""
    # 根据操作类型生成不同的消息文本
    action_text_map = {
        "远程开门": "远程开启了",
        "密码开门": "通过密码开启了",
        "指纹开门": "通过指纹开启了",
        "刷卡开门": "通过刷卡开启了",
    }
    action_text = action_text_map.get(action, "开启了")

    # 根据状态生成不同的消息
    if status == "成功":
        message = f"【{username}】{action_text}【{device_name}】({location})"
    else:
        message = f"【{username}】{action_text}【{device_name}】- {status}"

    return {
        "type": "door_open",
        "message": message,
        "username": username,
        "device_name": device_name,
        "location": location or "",
        "action": action,
        "status": status,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device_id": device_id
    }


async def _safe_send(websocket: WebSocket, msg: dict, manager_ref=None) -> bool:
    """安全发送 WebSocket 消息，发送失败则清理连接"""
    try:
        await websocket.send_json(msg)
        return True
    except Exception as e:
        logger.warning(f"WebSocket 推送失败，清理死连接: {e}")
        if manager_ref:
            manager_ref.disconnect(websocket)
        return False


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_info: Dict[int, dict] = {}

    def connect(self, websocket: WebSocket, user_id: int, permissions: dict):
        """
        连接时记录用户权限

        Args:
            websocket: WebSocket 连接
            user_id: 用户ID
            permissions: 用户权限字典 {"can_view_log": bool, "can_view_device": bool, "can_view_alert": bool}
        """
        self.active_connections.append(websocket)
        self.user_info[id(websocket)] = {
            "websocket": websocket,
            "user_id": user_id,
            **permissions
        }

    def disconnect(self, websocket: WebSocket):
        self.user_info.pop(id(websocket), None)
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def _get_bound_user_ids(self, device_id: int) -> set:
        """异步获取绑定了指定设备的用户 ID 集合"""
        def _query():
            db = SessionLocal()
            try:
                bindings = db.query(UserDevice.user_id).filter(UserDevice.device_id == device_id).all()
                return {b.user_id for b in bindings}
            finally:
                db.close()

        return await asyncio.to_thread(_query)

    async def send_door_event(self, device_id: int, username: str, device_name: str, location: str, action: str = "远程开门", status: str = "成功"):
        """向绑定了该设备的用户和有日志查看权限的用户推送开门事件"""
        msg = _build_door_msg(username, device_name, location, action, device_id, status)
        bound_user_ids = await self._get_bound_user_ids(device_id)

        for info in list(self.user_info.values()):
            if info.get("can_view_log") or info["user_id"] in bound_user_ids:
                await _safe_send(info["websocket"], msg, self)

    async def send_device_status(self, device_id: int, device_name: str, status: str, location: str = ""):
        """向有设备查看权限的用户推送设备状态变化（普通用户通过API查询获取）"""
        msg = {"type": "device_status", "device_id": device_id, "device_name": device_name, "status": status, "location": location}
        for info in list(self.user_info.values()):
            if info.get("can_view_device"):
                await _safe_send(info["websocket"], msg, self)

    async def send_alert_event(self, device_id: int, device_name: str, alert_type: str, message: str):
        """向有异常事件查看权限的用户推送告警"""
        msg = {
            "type": "alert",
            "alert_type": alert_type,
            "device_id": device_id,
            "device_name": device_name,
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        for info in list(self.user_info.values()):
            if info.get("can_view_alert"):
                await _safe_send(info["websocket"], msg, self)


manager = ConnectionManager()


async def _auth_fail(websocket: WebSocket, msg: str):
    """发送认证失败消息"""
    await websocket.send_json({"type": "auth", "status": "failed", "msg": msg})


async def authenticate_websocket(websocket: WebSocket) -> Optional[Tuple[int, dict]]:
    """WebSocket 认证，返回 (user_id, permissions) 或 None"""
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

    def _query_user():
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            permissions = {
                "can_view_log": user_has_permission(db, user, "log.view"),
                "can_view_device": user_has_permission(db, user, "device.view"),
                "can_view_alert": user_has_permission(db, user, "alert.view"),
            }
            return permissions
        finally:
            db.close()

    permissions = await asyncio.to_thread(_query_user)
    if permissions is None:
        await _auth_fail(websocket, "用户不存在")
        return None

    await websocket.send_json({"type": "auth", "status": "ok"})
    logger.info(f"WebSocket 认证成功: user_id={user_id}, permissions={permissions}")
    return user_id, permissions
