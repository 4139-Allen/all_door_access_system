"""
Pydantic Schema 校验单元测试

测试对象：schemas/user_schema.py 中的 Pydantic 模型
特点：纯逻辑验证，无外部依赖
"""
import pytest

try:
    from pydantic import ValidationError
    from schemas.user_schema import (
        UserLogin,
        UserCreate,
        PasswordChange,
        ProfileUpdate,
        ResetPassword,
    )
    HAS_SCHEMAS = True
except ImportError:
    HAS_SCHEMAS = False
    pytest.skip("无法导入 schemas.user_schema，跳过测试", allow_module_level=True)


class TestUserLoginSchema:
    """登录请求校验"""

    def test_valid_login(self):
        data = UserLogin(username="allen123", password="mypassword")
        assert data.username == "allen123"
        assert data.password == "mypassword"

    def test_username_with_chinese(self):
        data = UserLogin(username="张三", password="pass123456")
        assert data.username == "张三"

    def test_username_with_underscore(self):
        data = UserLogin(username="test_user_01", password="pass123456")
        assert data.username == "test_user_01"

    def test_empty_username(self):
        with pytest.raises(ValidationError):
            UserLogin(username="", password="pass123456")

    def test_username_with_special_chars(self):
        """含特殊字符的用户名应被拒绝"""
        with pytest.raises(ValidationError):
            UserLogin(username="user@name!", password="pass123456")

    def test_username_with_space(self):
        """用户名含空格应被拒绝"""
        with pytest.raises(ValidationError):
            UserLogin(username="user name", password="pass123456")

    def test_short_password(self):
        with pytest.raises(ValidationError):
            UserLogin(username="testuser", password="123")

    def test_missing_field(self):
        """缺少必填字段"""
        with pytest.raises(ValidationError):
            UserLogin(username="testuser")


class TestUserCreateSchema:
    """注册请求校验"""

    def test_valid_create(self):
        data = UserCreate(username="newuser", password="pass123456")
        assert data.role == "user"  # 默认角色

    def test_custom_role(self):
        data = UserCreate(username="newadmin", password="pass123456", role="admin")
        assert data.role == "admin"

    def test_username_too_long(self):
        with pytest.raises(ValidationError):
            UserCreate(
                username="a" * 51,
                password="pass123456",
            )


class TestPasswordChangeSchema:
    """修改密码请求校验"""

    def test_valid_change(self):
        data = PasswordChange(
            old_password="oldpass123",
            new_password="newpass456",
        )
        assert data.old_password == "oldpass123"
        assert data.new_password == "newpass456"

    def test_change_without_old_password(self):
        """未设置密码的用户（old_password 可空）"""
        data = PasswordChange(new_password="newpass456")
        assert data.old_password is None

    def test_new_password_too_short(self):
        with pytest.raises(ValidationError):
            PasswordChange(new_password="123")

    def test_new_password_too_long(self):
        with pytest.raises(ValidationError):
            PasswordChange(new_password="a" * 73)


class TestProfileUpdateSchema:
    """修改用户名请求校验"""

    def test_valid_update(self):
        data = ProfileUpdate(username="newname")
        assert data.username == "newname"

    def test_empty_username(self):
        with pytest.raises(ValidationError):
            ProfileUpdate(username="")


class TestResetPasswordSchema:
    """重置密码请求校验"""

    def test_valid_reset(self):
        data = ResetPassword(
            phone="13800138000",
            code="123456",
            new_password="newpass123",
        )
        assert data.phone == "13800138000"
        assert len(data.new_password) >= 6

    def test_code_too_short(self):
        with pytest.raises(ValidationError):
            ResetPassword(
                phone="13800138000",
                code="12",
                new_password="newpass123",
            )

    def test_new_password_too_short(self):
        with pytest.raises(ValidationError):
            ResetPassword(
                phone="13800138000",
                code="123456",
                new_password="123",
            )


class TestUsernameValidation:
    """用户名校验规则"""

    @pytest.mark.parametrize("valid_name", [
        "admin",
        "test_user",
        "张三",
        "user123",
        "abc_123_张三",
        "A",
    ])
    def test_valid_usernames(self, valid_name):
        UserLogin(username=valid_name, password="pass123456")

    @pytest.mark.parametrize("invalid_name", [
        "",
        "user@name",
        "user name",
        "user.name",
        "user-name",
        "a" * 51,
    ])
    def test_invalid_usernames(self, invalid_name):
        with pytest.raises(ValidationError):
            UserLogin(username=invalid_name, password="pass123456")
