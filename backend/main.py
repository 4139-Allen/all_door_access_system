import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routers import routers
from core.config import ALLOWED_ORIGINS
from database.db import init_database, drop_all_tables
from fastapi import Request
from utils.api_exception_handler import error
# 导入封装好的日志类
from utils.logger import AppLogger
from contextlib import asynccontextmanager
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ===== 启动时执行 =====

    # 抑制 uvicorn 自带 access log（我们的 log_requests 中间件已接管请求日志）
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    app_logger = AppLogger.get_logger()
    app_logger.info("=" * 50)
    app_logger.info("🚀 门禁管理系统正在启动...")
    app_logger.info("=" * 50)

    # 1. 初始化数据库（建库 + 建表）
    try:
        # 如需重置数据库，取消下一行注释并重启（⚠️ 会清空所有数据）
        # drop_all_tables()
        init_database()
    except Exception as e:
        app_logger.error(f"⚠️ 数据库初始化失败，服务将无法正常运行: {e}")

    # 2. 初始化管理员账户
    try:
        from services.admin_user_service import init_admin
        init_admin()
    except Exception as e:
        app_logger.error(f"⚠️ 管理员初始化失败: {e}")

    # 2.5 初始化权限数据（角色 + 权限 + 分配）
    try:
        from database.db import SessionLocal
        from services.permission_service import init_permissions
        db = SessionLocal()
        init_permissions(db)
        db.close()
    except Exception as e:
        app_logger.error(f"⚠️ 权限初始化失败: {e}")

    # 2.5 重置所有设备为离线状态（重启后 Redis 缓存丢失）
    try:
        from database.db import SessionLocal
        from database.models.device import Device
        db = SessionLocal()
        db.query(Device).update({Device.status: "offline"})
        db.commit()
        db.close()
        app_logger.info("📋 已重置所有设备为离线状态")
    except Exception as e:
        app_logger.error(f"⚠️ 重置设备状态失败: {e}")

    # 3. 启动 MQTT 客户端
    try:
        from services.mqtt_service import mqtt_manager
        mqtt_manager.start()
    except Exception as e:
        app_logger.error(f"⚠️ MQTT 客户端启动失败: {e}")

    # 4. 启动设备状态监控
    try:
        from services.device_monitor_service import start_device_monitor
        start_device_monitor()
    except Exception as e:
        app_logger.error(f"⚠️ 设备状态监控启动失败: {e}")

    app_logger.info("=" * 50)
    app_logger.info("✅ 门禁管理系统服务启动成功 🚀")
    app_logger.info("📍 服务地址: http://127.0.0.1:8000")
    app_logger.info("📖 文档地址: http://127.0.0.1:8000/docs")
    app_logger.info("=" * 50)

    yield  # 应用运行期间

    # ===== 关闭时执行 =====
    app_logger.info("=" * 50)
    app_logger.info("🛑 门禁管理系统正在关闭...")
    app_logger.info("=" * 50)

    # 关闭 MQTT 连接
    try:
        from services.mqtt_service import mqtt_manager
        mqtt_manager.stop()
    except Exception as e:
        app_logger.error(f"MQTT 关闭失败: {e}")

    # 关闭设备状态监控
    try:
        from services.device_monitor_service import stop_device_monitor
        stop_device_monitor()
    except Exception as e:
        app_logger.error(f"设备状态监控关闭失败: {e}")



app = FastAPI(title="门禁管理系统", version="1.0", lifespan=lifespan)  #  传入 lifespan

# # 删除所有表
# Base.metadata.drop_all(bind=engine)

# CORS 跨域（* 与 allow_credentials 不兼容，浏览器会拒绝）
allow_all_origins = "*" in ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else ALLOWED_ORIGINS,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有 HTTP 请求"""
    start_time = time.time()
    
    # 执行请求
    response = await call_next(request)
    
    # 计算耗时
    duration = time.time() - start_time
    
    # 获取客户端 IP
    client_host = request.client.host if request.client else "unknown"
    
    # 记录日志（跳过健康检查和静态文件）
    # 使用 DEBUG 级别避免 INFO 刷屏；需要追踪请求时设 LOG_LEVEL=DEBUG
    if not request.url.path.startswith("/health"):
        logger = AppLogger.get_logger()
        logger.debug(
            f"📊 {request.method} {request.url.path} | "
            f"状态: {response.status_code} | "
            f"耗时: {duration:.3f}s | "
            f"IP: {client_host}"
        )
    
    return response

# 静态文件服务（头像等上传文件）
os.makedirs("uploads/avatars", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 路由
app.include_router(routers, prefix="/api")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，捕获所有未处理的异常"""
    logger = AppLogger.get_logger()
    logger.error(
        f"💥 未处理的异常 | "
        f"[{request.method} {request.url}] | "
        f"错误: {str(exc)}",
        exc_info=True  # 记录完整堆栈
    )

    return error(msg="服务器内部错误", code=500)


# 健康检查端点（检测 MySQL 和 Redis 连通性，Docker 据此判定服务是否真正常）
@app.get("/health", summary="健康检查")
def health_check():
    from database.db import SessionLocal
    from database.redis import redis_client
    from sqlalchemy import text

    checks = {"database": "unknown", "redis": "unknown"}
    http_status = 200

    # 检查 MySQL
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        http_status = 503

    # 检查 Redis
    try:
        client = redis_client.get_client()
        if client and client.ping():
            checks["redis"] = "ok"
        else:
            checks["redis"] = "error: no connection"
            http_status = 503
    except Exception as e:
        checks["redis"] = f"error: {e}"
        http_status = 503

    overall = "healthy" if http_status == 200 else "degraded"
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=http_status,
        content={"status": overall, "service": "door_access_system", "checks": checks}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
