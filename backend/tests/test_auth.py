"""
认证模块单元测试
测试 JWT Token 创建、验证、密码哈希等功能
"""
import pytest
from utils.auth import hash_password, verify_password, create_access_token, get_current_user, logout_token
from jose import jwt, JWTError
from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
from database.redis import redis_client


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password_creates_hash(self):
        """测试密码能够成功哈希"""
        password = "testpass123"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert isinstance(hashed, str)

    def test_verify_password_correct(self):
        """测试正确密码验证通过"""
        password = "testpass123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证失败"""
        hashed = hash_password("correctpass")

        assert verify_password("wrongpass", hashed) is False

    def test_hash_password_too_long(self):
        """测试超长密码抛出异常"""
        long_password = "a" * 100

        with pytest.raises(ValueError, match="密码过长"):
            hash_password(long_password)

    def test_verify_password_too_long(self):
        """测试超长密码验证返回 False"""
        hashed = hash_password("shortpass")
        long_password = "a" * 100

        assert verify_password(long_password, hashed) is False

    def test_different_hashes_for_same_password(self):
        """测试相同密码生成不同的哈希值（bcrypt 特性）"""
        password = "testpass123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_hash_password_empty_string(self):
        """测试空字符串密码"""
        hashed = hash_password("")
        assert hashed is not None
        assert verify_password("", hashed) is True

    def test_hash_password_special_characters(self):
        """测试特殊字符密码"""
        password = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_password_unicode(self):
        """测试 Unicode 字符密码"""
        password = "密码测试🔐中文"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_password_exactly_72_bytes(self):
        """测试正好72字节的密码（边界值）"""
        password = "a" * 72
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_password_73_bytes(self):
        """测试73字节的密码（超过限制）"""
        password = "a" * 73
        with pytest.raises(ValueError, match="密码过长"):
            hash_password(password)


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


class TestPasswordEdgeCases:
    """密码边界情况测试"""

    def test_password_case_sensitivity(self):
        """测试密码大小写敏感"""
        password = "TestPass123"
        hashed = hash_password(password)

        assert verify_password("TestPass123", hashed) is True
        assert verify_password("testpass123", hashed) is False
        assert verify_password("TESTPASS123", hashed) is False

    def test_password_with_spaces(self):
        """测试包含空格的密码"""
        password = "test pass 123"
        hashed = hash_password(password)

        assert verify_password("test pass 123", hashed) is True
        assert verify_password("testpass123", hashed) is False

    def test_password_numeric_only(self):
        """测试纯数字密码"""
        password = "123456789"
        hashed = hash_password(password)

        assert verify_password("123456789", hashed) is True

    def test_password_minimum_length(self):
        """测试最短密码（1个字符）"""
        password = "a"
        hashed = hash_password(password)

        assert verify_password("a", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_password_similar_but_different(self):
        """测试相似但不同的密码"""
        password1 = "password123"
        password2 = "password124"

        hashed1 = hash_password(password1)
        assert verify_password(password1, hashed1) is True
        assert verify_password(password2, hashed1) is False
