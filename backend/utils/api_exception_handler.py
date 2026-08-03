import asyncio
import inspect
import json
from functools import wraps

from fastapi import FastAPI, Request, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError
from starlette.exceptions import HTTPException as StarletteHTTPException

from utils.logger import AppLogger
from core.response_schema import error
from core.exceptions import NotFoundError, AuthError, TooManyRequestsError

logger = AppLogger.get_logger()

# Pydantic v2 核心校验异常（不继承 ValueError，需单独处理）
try:
    from pydantic_core import ValidationError as PydanticCoreValidationError
except ImportError:
    PydanticCoreValidationError = None


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
        # Pydantic 校验错误 → 转 422（model_validator 抛出的 core 错误不继承 ValueError）
        if (PydanticCoreValidationError and isinstance(e, PydanticCoreValidationError)):
            errors = e.errors() if hasattr(e, "errors") else [{"msg": str(e)}]
            first = errors[0] if errors else {}
            msg = first.get("msg", "请求参数校验失败")
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
            logger.warning(f"请求参数校验失败 [{name}]: {msg}")
            return JSONResponse(status_code=422, content=error(msg, code=422))

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
        logger.warning(f"认证失败 [{request.method} {request.url.path}]: {str(exc)}")
        return JSONResponse(status_code=401, content=error(str(exc), code=401))

    @app.exception_handler(PermissionError)
    async def _permission_error_handler(request: Request, exc: PermissionError):
        logger.warning(f"权限错误 [{request.method} {request.url.path}]: {str(exc)}")
        return JSONResponse(status_code=403, content=error(str(exc), code=403))

    @app.exception_handler(NotFoundError)
    async def _not_found_handler(request: Request, exc: NotFoundError):
        logger.warning(f"资源不存在 [{request.method} {request.url.path}]: {str(exc)}")
        return JSONResponse(status_code=404, content=error(str(exc), code=404))

    @app.exception_handler(TooManyRequestsError)
    async def _too_many_requests_handler(request: Request, exc: TooManyRequestsError):
        logger.warning(f"请求频率过高 [{request.method} {request.url.path}]: {str(exc)}")
        return JSONResponse(status_code=429, content=error(str(exc), code=429))

    # Pydantic v2 核心校验错误（model_validator 抛出，不继承 ValueError）
    if PydanticCoreValidationError:
        @app.exception_handler(PydanticCoreValidationError)
        async def _pydantic_core_validation_handler(request: Request, exc: PydanticCoreValidationError):
            errors = exc.errors() if hasattr(exc, "errors") else [{"msg": str(exc)}]
            first = errors[0] if errors else {}
            msg = first.get("msg", "请求参数校验失败")
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
            logger.warning(f"请求参数校验失败 [{request.method} {request.url.path}]: {msg}")
            return JSONResponse(status_code=422, content=error(msg, code=422))

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError):
        """Pydantic 请求参数校验失败 → 统一中文错误提示"""
        field_names = {
            "username": "用户名",
            "password": "密码",
            "new_password": "新密码",
            "old_password": "原密码",
            "phone": "手机号",
            "email": "邮箱",
            "name": "名称",
            "location": "位置",
            "code": "验证码",
            "user_id": "用户ID",
            "device_id": "设备ID",
            "device_name": "设备名称",
            "status": "状态",
            "action": "操作类型",
            "start_time": "开始时间",
            "end_time": "结束时间",
            "page": "页码",
            "size": "每页条数",
            "role": "角色",
            "alert_type": "事件类型",
            "target": "接收目标",
            "avatar": "头像",
            "captcha": "验证码",
            "ip": "IP地址",
        }

        errors = exc.errors()
        if not errors:
            return JSONResponse(status_code=422, content=error("请求参数校验失败", code=422))

        first = errors[0]
        loc = first.get("loc", [])
        # 取 loc 最后一段作为字段名（如 ["body", "password"] → "password"）
        raw_field = str(loc[-1]) if loc else ""
        cn_field = field_names.get(raw_field, raw_field)
        err_type = first.get("type", "")
        ctx = first.get("ctx") or {}

        if err_type == "string_too_short":
            min_len = ctx.get("min_length", "")
            msg = f"{cn_field}长度不能少于{min_len}个字符"
        elif err_type == "string_too_long":
            max_len = ctx.get("max_length", "")
            msg = f"{cn_field}长度不能超过{max_len}个字符"
        elif err_type in ("missing", "value_error.missing"):
            msg = f"{cn_field}不能为空"
        elif err_type in ("datetime_parsing", "date_parsing", "datetime_from_date_parsing", "date_from_datetime_parsing"):
            msg = f"{cn_field}格式错误，请使用 YYYY-MM-DD HH:mm:ss 格式"
        elif err_type == "int_parsing":
            msg = f"{cn_field}必须为数字"
        elif err_type == "string_type":
            # 非字符串类型（null / 数字等）传给 str 字段
            msg = f"{cn_field}必须为字符串"
        elif err_type == "greater_than_equal":
            msg = f"{cn_field}不能小于{ctx.get('ge', '')}"
        elif err_type == "less_than_equal":
            msg = f"{cn_field}不能超过{ctx.get('le', '')}"
        elif err_type == "value_error":
            # 自定义 field_validator 抛出的 ValueError
            # Pydantic v2 会给 msg 加上 "Value error, " 前缀，需要去掉
            msg = first.get("msg", "")
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
            if not msg:
                msg = f"{cn_field}格式错误"
        elif err_type == "literal_error":
            # Literal 枚举校验失败（如 alert_type 只能取 lock/offline/error）
            expected = ctx.get("expected", "")
            msg = f"{cn_field}取值不合法，只能为: {expected}"
        else:
            msg = first.get("msg", f"{cn_field}格式错误")

        logger.warning(f"请求参数校验失败 [{request.method} {request.url.path}]: {msg}")
        return JSONResponse(status_code=422, content=error(msg, code=422))

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            msg = "接口不存在"
        elif exc.status_code == 405:
            msg = "请求方法不允许"
        elif exc.status_code == 500:
            msg = "服务器内部错误"
        else:
            msg = exc.detail or "请求失败"
        logger.warning(f"HTTP {exc.status_code} [{request.method} {request.url.path}]: {msg}")
        return JSONResponse(status_code=exc.status_code, content=error(msg, code=exc.status_code))
