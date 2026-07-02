"""
密码哈希单元测试（纯 bcrypt，无外部依赖）
测试密码哈希、验证、边界情况
"""
import pytest
from utils.auth import hash_password, verify_password


class TestPasswordHashing:
    """密码哈希基础测试"""

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
