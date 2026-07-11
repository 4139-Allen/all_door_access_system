"""
密码工具单元测试

测试对象：utils/auth.py 中的 hash_password / verify_password
特点：纯逻辑，无外部依赖，速度快
"""
import pytest

# 注意：这里直接导入项目代码，因为单元测试在项目目录下运行
try:
    from utils.auth import hash_password, verify_password
    HAS_AUTH_MODULE = True
except ImportError:
    HAS_AUTH_MODULE = False
    pytest.skip("无法导入 utils.auth，跳过密码测试", allow_module_level=True)


class TestPasswordHashing:
    """密码哈希与验证"""

    def test_hash_and_verify(self):
        """正常密码：哈希后可正确验证"""
        password = "MySecureP@ss123"
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_wrong_password(self):
        """错误密码：验证不通过"""
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)

    def test_empty_string(self):
        """空字符串密码"""
        hashed = hash_password("a")
        # 空字符串可能触发不同校验路径
        assert not verify_password("", hashed)

    def test_unicode_password(self):
        """Unicode 密码"""
        password = "密码测试🔑"
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_numeric_password(self):
        """纯数字密码"""
        password = "1234567890"
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_special_chars(self):
        """特殊字符密码"""
        password = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_max_length_password(self):
        """72 字节边界测试（bcrypt 限制）"""
        # 刚好 72 字节
        password = "a" * 72
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_exceed_max_length(self):
        """超过 72 字节抛出异常"""
        with pytest.raises(ValueError, match="密码过长"):
            hash_password("a" * 73)

    def test_verify_exceed_max_length(self):
        """验证超过 72 字节的密码返回 False（不抛异常）"""
        assert not verify_password("a" * 73, "$2b$12$...")

    def test_different_passwords(self):
        """不同密码的哈希值不同"""
        hash1 = hash_password("password123")
        hash2 = hash_password("password456")
        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """同一密码每次哈希结果不同（bcrypt 加盐）"""
        hash1 = hash_password("same_password")
        hash2 = hash_password("same_password")
        assert hash1 != hash2

    def test_verify_against_stored_hash(self):
        """验证已存储的哈希可以正常工作"""
        stored_hash = hash_password("my_password")
        assert verify_password("my_password", stored_hash)
        assert not verify_password("other_password", stored_hash)


class TestPasswordEdgeCases:
    """密码边界情况"""

    def test_minimal_password(self):
        """最短密码（6位）"""
        password = "abcd12"  # 6 位
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_password_with_spaces(self):
        """密码含空格"""
        password = "pass word 123"
        hashed = hash_password(password)
        assert verify_password(password, hashed)
