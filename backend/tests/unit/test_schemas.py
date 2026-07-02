"""
Schema 验证测试（纯 Pydantic，无外部依赖）
测试请求/响应模型的字段校验逻辑
"""
import pytest
from pydantic import ValidationError
from schemas.device_schema import DeviceCreate, DeviceUpdate
from schemas.user_schema import UserCreate, UserLogin, PasswordChange
from schemas.door_schema import LogQuery


class TestDeviceCreateSchema:
    """设备创建 Schema 测试"""

    def test_valid_device_create(self):
        """测试有效的设备创建数据"""
        data = DeviceCreate(name="001", location="校门")

        assert data.name == "001"
        assert data.location == "校门"

    def test_device_create_missing_name(self):
        """测试缺少设备名称"""
        with pytest.raises(ValidationError):
            DeviceCreate(location="校门")

    def test_device_create_missing_location(self):
        """测试缺少设备位置"""
        with pytest.raises(ValidationError):
            DeviceCreate(name="001")


class TestDeviceUpdateSchema:
    """设备更新 Schema 测试"""

    def test_partial_update(self):
        """测试部分字段更新"""
        data = DeviceUpdate(name="002")

        assert data.name == "002"
        assert data.location is None
        assert data.status is None

    def test_full_update(self):
        """测试全部字段更新"""
        data = DeviceUpdate(name="002", location="教学楼", status="offline")

        assert data.name == "002"
        assert data.location == "教学楼"
        assert data.status == "offline"


class TestUserCreateSchema:
    """用户创建 Schema 测试"""

    def test_valid_user_create(self):
        """测试有效的用户创建数据"""
        data = UserCreate(username="newuser", password="pass123")

        assert data.username == "newuser"
        assert data.password == "pass123"

    def test_user_create_short_password(self):
        """测试密码过短"""
        with pytest.raises(ValidationError):
            UserCreate(username="newuser", password="123")

    def test_user_create_long_username(self):
        """测试用户名过长"""
        long_username = "a" * 100
        with pytest.raises(ValidationError):
            UserCreate(username=long_username, password="pass123")


class TestUserLoginSchema:
    """用户登录 Schema 测试"""

    def test_valid_login(self):
        """测试有效的登录数据"""
        data = UserLogin(username="testuser", password="pass123")

        assert data.username == "testuser"
        assert data.password == "pass123"

    def test_login_missing_fields(self):
        """测试缺少必填字段"""
        with pytest.raises(ValidationError):
            UserLogin(username="testuser")


class TestPasswordChangeSchema:
    """密码修改 Schema 测试"""

    def test_valid_password_change(self):
        """测试有效的密码修改数据"""
        data = PasswordChange(old_password="old123", new_password="new456")

        assert data.old_password == "old123"
        assert data.new_password == "new456"

    def test_password_change_short_new_password(self):
        """测试新密码过短"""
        with pytest.raises(ValidationError):
            PasswordChange(old_password="old123", new_password="123")


class TestLogQuerySchema:
    """日志查询 Schema 测试"""

    def test_default_pagination(self):
        """测试默认分页参数"""
        data = LogQuery()

        assert data.page == 1
        assert data.size == 10

    def test_custom_pagination(self):
        """测试自定义分页参数"""
        data = LogQuery(page=2, size=20)

        assert data.page == 2
        assert data.size == 20

    def test_invalid_page_number(self):
        """测试无效页码"""
        with pytest.raises(ValidationError):
            LogQuery(page=0)

    def test_invalid_page_size(self):
        """测试无效每页数量"""
        with pytest.raises(ValidationError):
            LogQuery(size=0)
