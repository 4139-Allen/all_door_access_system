"""
数据库校验工具（可选）

职责：
  通过直连数据库验证 API 操作的数据结果，作为 HTTP 断言之外的
  双重保障。常用于验证数据持久化正确性。

用法：
    from test_util.db_util import DBUtil

    db = DBUtil(host="...", user="...", password="...", db="...")
    user = db.query_one("SELECT * FROM users WHERE username=%s", ("test_user",))
    assert user["role"] == "user"
"""

import logging
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

logger = logging.getLogger("auto_test")


class DBUtil:
    """数据库校验工具"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "door_access_system",
        env_config: dict = None,
    ):
        """
        初始化数据库连接

        参数：
            env_config: 环境配置字典（优先级高，会覆盖 host/port 等参数）
            host/port/user/password/database: 直接指定（env_config 为 None 时生效）
        """
        if env_config:
            self.config = env_config
        else:
            self.config = {
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "db": database,
            }
        self._conn = None

    # ---------- 连接管理 ----------

    def connect(self):
        """建立数据库连接"""
        if self._conn is not None:
            return

        try:
            import pymysql
            self._conn = pymysql.connect(
                host=self.config["host"],
                port=int(self.config.get("port", 3306)),
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["db"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            logger.info("✅ 数据库连接成功")
        except ImportError:
            logger.warning("⚠️  未安装 pymysql，数据库校验功能不可用")
            self._conn = None
        except Exception as e:
            logger.warning(f"⚠️  数据库连接失败: {e}")
            self._conn = None

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def session(self):
        """提供 with 语句的数据库会话"""
        self.connect()
        if self._conn is None:
            yield None
            return
        try:
            yield self._conn
        finally:
            pass  # 外部 commit/rollback

    # ---------- 查询方法 ----------

    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        """查询单条记录"""
        self.connect()
        if self._conn is None:
            logger.warning("数据库未连接，跳过查询")
            return None
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def query_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        """查询多条记录"""
        self.connect()
        if self._conn is None:
            logger.warning("数据库未连接，跳过查询")
            return []
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def count(self, sql: str, params: tuple = ()) -> int:
        """查询计数"""
        self.connect()
        if self._conn is None:
            return -1
        with self._conn.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone()
            return list(result.values())[0] if result else 0

    # ---------- 常用校验 ----------

    def assert_user_exists(self, username: str) -> Optional[Dict]:
        """断言用户存在于数据库"""
        user = self.query_one(
            "SELECT id, username, role FROM users WHERE username=%s",
            (username,),
        )
        assert user is not None, f"❌ 用户 '{username}' 应存在于数据库，但未找到"
        return user

    def assert_user_not_exists(self, username: str):
        """断言用户不存在于数据库"""
        user = self.query_one(
            "SELECT id FROM users WHERE username=%s",
            (username,),
        )
        assert user is None, f"❌ 用户 '{username}' 应已被删除，但仍存在于数据库"

    def assert_device_exists(self, device_id: int) -> Optional[Dict]:
        """断言设备存在于数据库"""
        device = self.query_one(
            "SELECT id, name, status FROM devices WHERE id=%s",
            (device_id,),
        )
        assert device is not None, f"❌ 设备 id={device_id} 应存在于数据库，但未找到"
        return device

    def assert_binding_exists(self, user_id: int, device_id: int):
        """断言用户-设备绑定关系存在"""
        binding = self.query_one(
            "SELECT id FROM user_devices WHERE user_id=%s AND device_id=%s",
            (user_id, device_id),
        )
        assert binding is not None, (
            f"❌ 绑定关系应存在 (user_id={user_id}, device_id={device_id})"
        )

    def assert_binding_not_exists(self, user_id: int, device_id: int):
        """断言用户-设备绑定关系不存在"""
        binding = self.query_one(
            "SELECT id FROM user_devices WHERE user_id=%s AND device_id=%s",
            (user_id, device_id),
        )
        assert binding is None, (
            f"❌ 绑定关系应已解除 (user_id={user_id}, device_id={device_id})"
        )
