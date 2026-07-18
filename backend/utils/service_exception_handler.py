"""
服务层异常/事务
通用异常处理装饰器和工具函数
用于统一 Service 层的异常处理和日志记录
"""
import functools
import inspect
from typing import Callable
from sqlalchemy.orm import Session
from utils.logger import AppLogger

logger = AppLogger.get_logger()


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
                if isinstance(e, (ValueError, PermissionError)):
                    logger.warning(f"Service [{func.__name__}] 业务校验失败: {str(e)}")
                else:
                    logger.error(f"Service [{func.__name__}] 执行失败: {str(e)}", exc_info=True)
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
                if isinstance(e, (ValueError, PermissionError)):
                    logger.warning(f"Service [{func.__name__}] 业务校验失败: {str(e)}")
                else:
                    logger.error(f"Service [{func.__name__}] 执行失败: {str(e)}", exc_info=True)
                raise
        return sync_wrapper
