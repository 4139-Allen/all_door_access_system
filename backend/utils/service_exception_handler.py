"""
服务层异常/事务
事务兜底：异常时立即回滚，然后透传异常，由 API 层统一记录日志和返回响应。

注意：此装饰器只负责回滚事务并透传异常，
日志由上层（@handle_api_exception）统一记录，避免重复。
"""
import functools
import inspect
from typing import Callable
from sqlalchemy.orm import Session


def service_exception_handler(func: Callable) -> Callable:
    """
    Service 层异常处理装饰器

    自动处理数据库事务回滚和异常日志记录

    使用示例:
        @service_exception_handler
        def create_user(db: Session, data: UserCreate):
            # 业务逻辑
            pass
    """

    def _extract_db(args, kwargs):
        """从参数中提取 db session"""
        for arg in args:
            if isinstance(arg, Session):
                return arg
        return kwargs.get('db')

    is_async = inspect.iscoroutinefunction(func)

    if is_async:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            db = _extract_db(args, kwargs)
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if db:
                    db.rollback()
                raise
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            db = _extract_db(args, kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if db:
                    db.rollback()
                raise
        return sync_wrapper
