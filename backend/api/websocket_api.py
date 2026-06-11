from fastapi import APIRouter, WebSocket

from utils.api_exception_handler import handle_websocket_exception
from services.websocket_service import manager, authenticate_websocket

router = APIRouter()


@router.websocket("/ws")
@handle_websocket_exception
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # 认证（由服务层处理）
    result = await authenticate_websocket(websocket)
    if result is None:
        return

    user_id, permissions = result

    # 注册到连接管理器（连接断开由装饰器统一处理）
    await manager.connect(websocket, user_id=user_id, permissions=permissions)
    while True:
        await websocket.receive_text()
