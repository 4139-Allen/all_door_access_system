"""
JWT Token 集成测试
测试 Token 创建、解码、过期、黑名单等功能（依赖 Redis）
"""
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from utils.auth import create_access_token, logout_token
from database.redis import redis_client


class TestAccessToken:
    """Token 创建测试"""

    def test_create_access_token(self):
        """测试创建 Token"""
        data = {"sub": "123"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)

    def test_decode_access_token(self):
        """测试解码 Token"""
        data = {"sub": "123"}
        token = create_access_token(data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "123"
        assert "exp" in payload

    def test_token_contains_expiration(self):
        """测试 Token 包含过期时间"""
        data = {"sub": "456"}
        token = create_access_token(data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_token_expiration_time(self):
        """测试 Token 过期时间符合配置"""
        data = {"sub": "789"}
        token = create_access_token(data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)

        # 过期时间应该在当前时间的 ACCESS_TOKEN_EXPIRE_MINUTES 分钟后
        expected_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        actual_delta = exp_datetime - now

        # 允许 5 秒的误差
        assert abs((actual_delta - expected_delta).total_seconds()) < 5

    def test_token_with_multiple_claims(self):
        """测试 Token 包含多个声明"""
        data = {"sub": "123", "role": "admin", "username": "testuser"}
        token = create_access_token(data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "123"
        assert payload["role"] == "admin"
        assert payload["username"] == "testuser"

    def test_token_stored_in_redis(self):
        """测试 Token 存储在 Redis 中"""
        if not redis_client:
            pytest.skip("Redis 未配置")

        data = {"sub": "999"}
        token = create_access_token(data)

        # 验证 Redis 中存在该 token
        assert redis_client.exists(f"token:{token}")
        assert redis_client.get(f"token:{token}") == "999"

    def test_token_invalid_signature(self):
        """测试使用错误密钥解码 Token"""
        data = {"sub": "123"}
        token = create_access_token(data)

        # 使用错误的密钥解码应该失败
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong_secret_key", algorithms=[ALGORITHM])

    def test_token_tampered(self):
        """测试篡改后的 Token 无法解码"""
        data = {"sub": "123"}
        token = create_access_token(data)

        # 篡改 token
        tampered_token = token[:-5] + "XXXXX"

        with pytest.raises(JWTError):
            jwt.decode(tampered_token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_create_token_with_empty_sub(self):
        """测试创建 sub 为空的 Token"""
        data = {"sub": ""}

        with pytest.raises(ValueError):
            create_access_token(data)

    def test_create_token_without_sub(self):
        """测试创建不包含 sub 的 Token（预期会失败）"""
        data = {"username": "testuser"}

        with pytest.raises(ValueError):
            token = create_access_token(data)


class TestTokenExpiration:
    """Token 过期测试"""

    def test_expired_token_raises_error(self):
        """测试过期 Token 抛出异常"""
        # 手动创建一个已过期的 token
        expired_payload = {
            "sub": "123",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1)
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(JWTError):
            jwt.decode(expired_token, SECRET_KEY, algorithms=[ALGORITHM])

    def test_token_not_yet_expired(self):
        """测试未过期的 Token 可以正常解码"""
        future_payload = {
            "sub": "123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        future_token = jwt.encode(future_payload, SECRET_KEY, algorithm=ALGORITHM)

        payload = jwt.decode(future_token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "123"


class TestLogoutAndBlacklist:
    """退出登录和黑名单测试"""

    def test_logout_removes_token_from_redis(self):
        """测试退出登录后从 Redis 删除 Token"""
        if not redis_client:
            pytest.skip("Redis 未配置")

        data = {"sub": "123"}
        token = create_access_token(data)

        # 验证 token 在 Redis 中
        assert redis_client.exists(f"token:{token}")

        # 退出登录
        logout_token(token)

        # 验证 token 已从 Redis 删除
        assert not redis_client.exists(f"token:{token}")

    def test_logout_adds_to_blacklist(self):
        """测试退出登录后加入黑名单"""
        if not redis_client:
            pytest.skip("Redis 未配置")

        data = {"sub": "123"}
        token = create_access_token(data)

        # 退出登录
        logout_token(token)

        # 验证已加入黑名单
        assert redis_client.exists(f"blacklist:{token}")
        assert redis_client.get(f"blacklist:{token}") == "true"

    def test_blacklist_expiration_time(self):
        """测试黑名单过期时间为 24 小时"""
        if not redis_client:
            pytest.skip("Redis 未配置")

        data = {"sub": "123"}
        token = create_access_token(data)

        logout_token(token)

        # 获取黑名单的剩余生存时间
        ttl = redis_client.ttl(f"blacklist:{token}")

        # 应该在 86400 秒（24小时）左右，允许 5 秒误差
        assert 86395 <= ttl <= 86405
