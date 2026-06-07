"""
Redis 连接管理
支持自动重连，连接失败后每次操作都会自动重试
"""
import json
import redis
from redis.exceptions import RedisError
from core.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
from utils.logger import AppLogger

logger = AppLogger.get_logger()


class RedisCli:
    """Redis 连接管理器，支持自动重连"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._client = None
            cls._instance = instance
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._connect()
            self._initialized = True

    def _connect(self):
        """尝试连接 Redis"""
        try:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2
            )
            client.ping()
            self._client = client
            logger.info("✅ Redis 连接成功")
        except RedisError as e:
            self._client = None
            logger.warning(f"⚠️ Redis 未连接: {e}，将在下次访问时重试")

    def get_client(self):
        """获取 Redis 客户端，断线时自动重连"""
        if self._client is None:
            self._connect()
        return self._client

    def __bool__(self):
        return self._client is not None

    def __getattr__(self, name):
        """透明代理 Redis 方法，断线时自动重连"""
        if name.startswith('_'):
            raise AttributeError(name)

        client = self.get_client()
        if client is None:
            logger.warning(f"Redis 不可用，操作 '{name}' 已跳过")
            def noop(*args, **kwargs):
                return None if name != 'keys' else []
            return noop
        return getattr(client, name)


redis_client = RedisCli()


def cache_get_json(key):
    """从 Redis 获取缓存并解析 JSON，无缓存或 Redis 不可用时返回 None"""
    client = redis_client.get_client()
    if client:
        try:
            data = client.get(key)
            if data:
                return json.loads(data)
        except RedisError as e:
            logger.warning(f"Redis 读取缓存失败 [{key}]: {e}")
            redis_client._client = None  # 触发下次重连
    return None


def cache_set_json(key, data, expire_seconds):
    """将数据序列化为 JSON 并存入 Redis"""
    client = redis_client.get_client()
    if client:
        try:
            client.setex(key, expire_seconds, json.dumps(data, ensure_ascii=False))
        except RedisError as e:
            logger.warning(f"Redis 写入缓存失败 [{key}]: {e}")
            redis_client._client = None  # 触发下次重连
