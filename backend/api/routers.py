# 1. 导入核心包
from fastapi import APIRouter

# 2. 导入子路由
from api.auth_api import router as auth_router
from api.admin_user_api import router as admin_user_router
from api.door_api import router as door_router
from api.device_api import router as device_router
from api.stat_api import router as stat_router
from api.ai_agent import router as ai_router
from api.websocket_api import router as websocket_router
from api.wx_auth_api import router as wx_auth_router
from api.permission_api import router as permission_router
from api.alert_api import router as alert_router

# 3. 创建总路由
routers = APIRouter()

# 4. 注册子路由
routers.include_router(auth_router)         # 认证管理
routers.include_router(admin_user_router)   # 管理员用户管理
routers.include_router(door_router)         # 门禁管理
routers.include_router(device_router)       # 设备管理
routers.include_router(stat_router)         # 统计数据
routers.include_router(ai_router)           # AI智能助手
routers.include_router(websocket_router)    # WebSocket
routers.include_router(wx_auth_router)      # 微信小程序认证
routers.include_router(permission_router)   # 权限管理
routers.include_router(alert_router)        # 异常事件


