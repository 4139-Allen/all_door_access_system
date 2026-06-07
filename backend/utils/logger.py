import logging
import os
from logging.handlers import TimedRotatingFileHandler


class AppLogger:
    """
    全局日志类（按天轮转 + 控制台输出）
    """
    _logger = None

    @classmethod
    def get_logger(cls, log_name="app", log_level=logging.INFO):
        """单例模式获取 logger"""
        if cls._logger is not None:
            return cls._logger

        # 创建 logs 文件夹
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 日志格式
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

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
        console_handler = logging.StreamHandler()
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
