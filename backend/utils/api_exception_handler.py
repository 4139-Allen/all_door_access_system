import asyncio
import inspect
import json
from functools import wraps

from fastapi import FastAPI, Request, WebSocketDisconnect
from fastapi.responses import JSONResponse
from jose import JWTError

from utils.logger import AppLogger
from core.response_schema import error
from core.exceptions import NotFoundError, AuthError, TooManyRequestsError

logger = AppLogger.get_logger()


def handle_api_exception(func):
    """
    API 层统一异常处理装饰器（HTTP 路由专用，支持 sync 和 async 函数）

    自动捕获常见异常并返回统一格式的错误响应

    使用示例:
        @router.post("/users")
        @handle_api_exception
        def create_user(data: UserCreate, db: Session = Depends(get_db)):
            db_create_user(db, data.username, data.password)
            return success(msg="创建成功")
    """

    _is_async = inspect.iscoroutinefunction(func)

    def _handle_exception(e, name):
        if isinstance(e, ValueError):
            logger.warning(f"业务逻辑错误 [{name}]: {str(e)}")
            return JSONResponse(status_code=400, content=error(str(e), code=400))
        elif isinstance(e, PermissionError):
            logger.warning(f"权限错误 [{name}]: {str(e)}")
            return JSONResponse(status_code=403, content=error(str(e), code=403))
        elif isinstance(e, NotFoundError):
            logger.warning(f"资源不存在 [{name}]: {str(e)}")
            return JSONResponse(status_code=404, content=error(str(e), code=404))
        elif isinstance(e, AuthError):
            logger.warning(f"认证失败 [{name}]: {str(e)}")
            return JSONResponse(status_code=401, content=error(str(e), code=401))
        elif isinstance(e, TooManyRequestsError):
            logger.warning(f"请求频率过高 [{name}]: {str(e)}")
            return JSONResponse(status_code=429, content=error(str(e), code=429))
        elif isinstance(e, TimeoutError):
            logger.error(f"请求超时 [{name}]: {str(e)}")
            return JSONResponse(status_code=504, content=error(str(e), code=504))
        else:
            logger.error(f"服务器内部错误 [{name}]: {str(e)}", exc_info=True)
            return JSONResponse(status_code=500, content=error("服务器内部错误，请联系超级管理员", code=500))

    if _is_async:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                return _handle_exception(e, func.__name__)
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return _handle_exception(e, func.__name__)
        return sync_wrapper


def handle_websocket_exception(func):
    """
    WebSocket 层统一异常处理装饰器

    自动捕获常见异常并通过 WebSocket 发送错误消息

    使用示例:
        @router.websocket("/ws")
        @handle_websocket_exception
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            # ... 业务逻辑
    """

    @wraps(func)
    async def wrapper(websocket, *args, **kwargs):
        user_id = None
        try:
            result = await func(websocket, *args, **kwargs)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"WebSocket 认证超时 [{func.__name__}]")
            await websocket.send_json({"type": "auth", "status": "failed", "msg": "认证超时"})
        except json.JSONDecodeError:
            logger.warning(f"WebSocket 消息格式错误 [{func.__name__}]")
            await websocket.send_json({"type": "auth", "status": "failed", "msg": "消息格式错误"})
        except JWTError as e:
            logger.warning(f"WebSocket Token 无效 [{func.__name__}]: {str(e)}")
            await websocket.send_json({"type": "auth", "status": "failed", "msg": "Token 无效"})
        except ValueError as e:
            logger.warning(f"WebSocket 业务逻辑错误 [{func.__name__}]: {str(e)}")
            await websocket.send_json({"type": "error", "msg": str(e)})
        except PermissionError as e:
            logger.warning(f"WebSocket 权限错误 [{func.__name__}]: {str(e)}")
            await websocket.send_json({"type": "error", "msg": str(e)})
        except NotFoundError as e:
            logger.warning(f"WebSocket 资源不存在 [{func.__name__}]: {str(e)}")
            await websocket.send_json({"type": "error", "msg": str(e)})
        except AuthError as e:
            logger.warning(f"WebSocket 认证失败 [{func.__name__}]: {str(e)}")
            await websocket.send_json({"type": "error", "msg": str(e)})
        except WebSocketDisconnect:
            logger.info(f"WebSocket 断开连接 [{func.__name__}]")
        except Exception as e:
            logger.error(f"WebSocket 服务器内部错误 [{func.__name__}]: {str(e)}", exc_info=True)
            await websocket.send_json({"type": "error", "msg": "服务器内部错误"})
        finally:
            # 清理连接管理器
            from services.websocket_service import manager
            manager.disconnect(websocket)
            try:
                await websocket.close()
            except Exception:
                pass

    return wrapper


# ===================== App 级异常处理器 =====================
# `@handle_api_exception` 只覆盖路由层，依赖（如 get_current_user）抛出的异常
# 需要 app 级处理器来保证响应格式统一。


def register_exception_handlers(app: FastAPI):
    """在 FastAPI 应用上注册所有自定义异常处理器"""

    @app.exception_handler(AuthError)
    async def _auth_error_handler(request: Request, exc: AuthError):
        return JSONResponse(status_code=401, content=error(str(exc), code=401))

    @app.exception_handler(PermissionError)
    async def _permission_error_handler(request: Request, exc: PermissionError):
        return JSONResponse(status_code=403, content=error(str(exc), code=403))

    @app.exception_handler(NotFoundError)
    async def _not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content=error(str(exc), code=404))

    @app.exception_handler(TooManyRequestsError)
    async def _too_many_requests_handler(request: Request, exc: TooManyRequestsError):
        return JSONResponse(status_code=429, content=error(str(exc), code=429))
