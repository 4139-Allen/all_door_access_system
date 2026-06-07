"""
服务层异常/事务
通用异常处理装饰器和工具函数
用于统一 Service 层的异常处理和日志记录
"""
import functools
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

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 从参数中提取 db session
        db = None
        for arg in args:
            if isinstance(arg, Session):
                db = arg
                break

        if not db:
            db = kwargs.get('db')

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            # 如果有 db session，执行回滚
            if db:
                db.rollback()

            # 记录错误日志
            logger.error(f"Service [{func.__name__}] 执行失败: {str(e)}", exc_info=True)

            # 抛出异常
            raise

    return wrapper
