import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger


class AppLogger:
    """
    全局日志类（支持结构化 JSON 日志）

    环境变量：
        LOG_FORMAT: 日志格式
            - "json" - JSON 格式（生产环境推荐）
            - "text" - 纯文本格式（开发环境默认）
        LOG_LEVEL: 日志级别（默认 INFO）
            - "DEBUG" - 含请求追踪日志
            - "INFO" - 仅业务事件
            - "WARNING" - 仅警告和错误

    使用方法：
        from utils.logger import AppLogger
        logger = AppLogger.get_logger()

        # 基础日志
        logger.info("用户登录成功")

        # 带上下文的日志（会自动添加到 JSON 字段）
        logger.info("开门成功", extra={
            "user_id": 1,
            "device_id": "001",
            "action": "door_open"
        })
    """
    _logger = None

    @classmethod
    def get_logger(cls, log_name="app", log_level=None):
        """单例模式获取 logger"""
        if cls._logger is not None:
            return cls._logger

        # 从环境变量读取日志级别（默认 INFO）
        if log_level is None:
            level_name = os.getenv("LOG_LEVEL", "INFO").upper()
            log_level = getattr(logging, level_name, logging.INFO)

        # 创建日志目录（可通过 LOG_DIR 环境变量自定义，用于测试环境）
        log_dir = os.getenv("LOG_DIR")
        if not log_dir:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 从环境变量读取日志格式配置
        log_format = os.getenv("LOG_FORMAT", "text").lower()

        # 根据格式选择 formatter
        if log_format == "json":
            formatter = cls._create_json_formatter()
        else:
            formatter = cls._create_text_formatter()

        # 1. 按天轮转文件日志
        file_handler = TimedRotatingFileHandler(
            filename=os.path.join(log_dir, f"{log_name}.log"),
            when="midnight",  # 每天凌晨切割
            interval=1,
            backupCount=30,  # 保留 30 天
            encoding="utf-8",
            delay=True
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)

        # 2. 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)

        # 3. 配置 logger
        logger = logging.getLogger(log_name)
        logger.setLevel(log_level)
        logger.handlers.clear()  # 清空旧 handler
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.propagate = False

        cls._logger = logger
        return logger

    @staticmethod
    def _create_json_formatter():
        """创建 JSON 格式的 formatter"""
        class CustomJsonFormatter(jsonlogger.JsonFormatter):
            def add_fields(self, log_record, record, message_dict):
                super().add_fields(log_record, record, message_dict)

                # 添加标准字段
                log_record['timestamp'] = self.formatTime(record)
                log_record['level'] = record.levelname
                log_record['logger'] = record.name
                log_record['module'] = record.module
                log_record['function'] = record.funcName
                log_record['line'] = record.lineno

                # 添加进程信息
                log_record['pid'] = os.getpid()

                # 移除重复字段
                if 'name' in log_record:
                    del log_record['name']

        return CustomJsonFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s',
            json_ensure_ascii=False
        )

    @staticmethod
    def _create_text_formatter():
        """创建纯文本格式的 formatter"""
        return logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


# 便捷函数
def get_logger(log_name="app", log_level=None):
    """获取 logger 的便捷函数"""
    return AppLogger.get_logger(log_name, log_level)
