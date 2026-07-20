"""
简单的内存频率限制器
用于登录等敏感接口的暴力破解防护
"""
import os
import time
import threading
from collections import defaultdict
from utils.logger import AppLogger
from core.exceptions import TooManyRequestsError

logger = AppLogger.get_logger()


class RateLimiter:
    """滑动窗口频率限制器"""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        """
        参数:
            max_attempts: 窗口内最大尝试次数
            window_seconds: 时间窗口（秒）
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._records: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        """
        检查是否允许请求
        返回 True 表示允许，False 表示被限制
        """
        # 设置 DISABLE_RATE_LIMIT=true 可完全跳过频率限制（测试/CI 环境）
        if os.getenv("DISABLE_RATE_LIMIT", "").lower() in ("true", "1", "yes"):
            return True
        # 兼容旧方式：库名以 _test 或 _staging 结尾自动跳过
        db_name = os.getenv("MYSQL_DB", "")
        if db_name.endswith("_test") or db_name.endswith("_staging"):
            return True

        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            records = self._records[key]
            # 清理过期的记录
            records[:] = [t for t in records if t > cutoff]
            records.append(now)

            if len(records) > self.max_attempts:
                retry_after = int(records[0] + self.window_seconds - now)
                logger.warning(f"频率限制触发 | key: {key} | {self.max_attempts}次/{self.window_seconds}秒")
                raise TooManyRequestsError(
                    f"请求过于频繁，请 {max(retry_after, 1)} 秒后再试"
                )
            return True

    def clear(self, key: str = None):
        """清除指定 key 或所有记录（用于测试）"""
        with self._lock:
            if key:
                self._records.pop(key, None)
            else:
                self._records.clear()


# 登录接口专用：5次/60秒
login_limiter = RateLimiter(max_attempts=5, window_seconds=60)
