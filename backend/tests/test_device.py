"""
设备服务单元测试
测试设备 CRUD、权限检查、缓存管理等功能
"""
import pytest
from services.device_service import (
    create_device,
    update_device,
    delete_device,
    get_device_list,
    check_user_permission,
    bind_user_device,
    unbind_user_device
)
from database.models.device import Device
from database.models.user_device import UserDevice
from schemas.device_schema import DeviceCreate, DeviceUpdate


class TestCheckUserPermission:
    """权限检查测试"""

    def test_user_has_permission(self, db_session, test_user, test_device):
        """测试用户有权限访问设备"""
        binding = UserDevice(user_id=test_user.id, device_id=test_device.id)
        db_session.add(binding)
        db_session.commit()

        assert check_user_permission(db_session, test_user.id, test_device.id) is True

    def test_user_no_permission(self, db_session, test_user, test_device):
        """测试用户无权限访问设备"""
        assert check_user_permission(db_session, test_user.id, test_device.id) is False


class TestCreateDevice:
    """创建设备测试"""

    def test_create_device_success(self, db_session):
        """测试成功创建设备"""
        data = DeviceCreate(name="002", location="教学楼")
        device = create_device(db_session, data)

        assert device.id is not None
        assert device.name == "002"
        assert device.location == "教学楼"
        assert device.status == "online"

    def test_create_device_with_empty_name(self, client, admin_headers):
        """测试创建空名称设备（预期参数校验失败）"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            data = DeviceCreate(name="", location="教学楼")

    def test_create_device_empty_location(self, db_session):
        """测试创建空位置设备抛出异常"""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            data = DeviceCreate(name="099", location="")

    def test_create_duplicate_device(self, db_session):
        """测试创建重复设备抛出异常"""
        data = DeviceCreate(name="001", location="校门")
        create_device(db_session, data)

        duplicate_data = DeviceCreate(name="001", location="校门")
        with pytest.raises(ValueError, match="已存在"):
            create_device(db_session, duplicate_data)


class TestUpdateDevice:
    """更新设备测试"""

    def test_update_device_name(self, db_session, test_device):
        """测试更新设备名称"""
        data = DeviceUpdate(name="002")
        updated = update_device(db_session, test_device.id, data)

        assert updated is not None
        assert updated.name == "002"

    def test_update_device_status(self, db_session, test_device):
        """测试更新设备状态"""
        data = DeviceUpdate(status="offline")
        updated = update_device(db_session, test_device.id, data)

        assert updated is not None
        assert updated.status == "offline"

    def test_update_device_location(self, db_session, test_device):
        """测试更新设备位置"""
        data = DeviceUpdate(location="图书馆")
        updated = update_device(db_session, test_device.id, data)

        assert updated is not None
        assert updated.location == "图书馆"

    def test_update_nonexistent_device(self, db_session):
        """测试更新不存在的设备返回 None"""
        data = DeviceUpdate(name="999")
        updated = update_device(db_session, 99999, data)

        assert updated is None


class TestDeleteDevice:
    """删除设备测试"""

    def test_delete_device_success(self, db_session):
        """测试成功删除设备"""
        device = Device(name="999", location="测试位置", status="online")
        db_session.add(device)
        db_session.commit()

        result = delete_device(db_session, device.id)

        assert result is True
        deleted = db_session.query(Device).filter(Device.id == device.id).first()
        assert deleted is None

    def test_delete_nonexistent_device(self, db_session):
        """测试删除不存在的设备抛出异常"""
        from core.exceptions import NotFoundError
        with pytest.raises( NotFoundError, match="设备不存在"):
            delete_device(db_session, 99999)

    def test_delete_bound_device(self, db_session, test_user):
        """测试删除已绑定用户的设备抛出异常"""
        device = Device(name="888", location="测试位置", status="online")
        db_session.add(device)
        db_session.commit()

        binding = UserDevice(user_id=test_user.id, device_id=device.id)
        db_session.add(binding)
        db_session.commit()

        with pytest.raises(ValueError, match="已绑定用户"):
            delete_device(db_session, device.id)


class TestGetDeviceList:
    """获取设备列表测试"""

    def test_admin_get_all_devices(self, db_session, test_admin, test_device):
        """测试管理员获取所有设备"""
        result = get_device_list(db_session, test_admin.id, test_admin.role, current_user=test_admin)

        assert result["total"] >= 1
        assert any(d["id"] == test_device.id for d in result["list"])

    def test_user_get_bound_devices(self, db_session, test_user, test_device):
        """测试普通用户只获取绑定的设备"""
        # 未绑定时应该返回空列表
        result = get_device_list(db_session, test_user.id, test_user.role, current_user=test_user)
        assert result["total"] == 0

        # 绑定后应该返回该设备
        binding = UserDevice(user_id=test_user.id, device_id=test_device.id)
        db_session.add(binding)
        db_session.commit()

        result = get_device_list(db_session, test_user.id, test_user.role, current_user=test_user)
        assert result["total"] == 1
        assert result["list"][0]["id"] == test_device.id

    def test_filter_devices_by_name(self, db_session, test_admin):
        """测试按名称筛选设备"""
        device1 = Device(name="001", location="校门", status="online")
        device2 = Device(name="002", location="教学楼", status="online")
        db_session.add_all([device1, device2])
        db_session.commit()

        result = get_device_list(db_session, test_admin.id, test_admin.role, name="001", current_user=test_admin)

        assert result["total"] == 1
        assert result["list"][0]["name"] == "001"


class TestBindUserDevice:
    """绑定用户设备测试"""

    def test_bind_success(self, db_session, test_user, test_device):
        """测试成功绑定用户和设备"""
        binding = bind_user_device(db_session, test_user.id, test_device.id)

        assert binding.id is not None
        assert binding.user_id == test_user.id
        assert binding.device_id == test_device.id

    def test_bind_duplicate(self, db_session, test_user, test_device):
        """测试重复绑定抛出异常"""
        bind_user_device(db_session, test_user.id, test_device.id)

        with pytest.raises(ValueError, match="已绑定"):
            bind_user_device(db_session, test_user.id, test_device.id)

    def test_bind_nonexistent_device(self, db_session, test_user):
        """测试绑定不存在的设备抛出异常"""
        from core.exceptions import NotFoundError
        with pytest.raises(NotFoundError, match="设备不存在"):
            bind_user_device(db_session, test_user.id, 99999)


class TestUnbindUserDevice:
    """解绑用户设备测试"""

    def test_unbind_success(self, db_session, test_user, test_device):
        """测试成功解绑"""
        binding = UserDevice(user_id=test_user.id, device_id=test_device.id)
        db_session.add(binding)
        db_session.commit()

        result = unbind_user_device(db_session, test_user.id, test_device.id)

        assert result is True
        deleted = db_session.query(UserDevice).filter(
            UserDevice.user_id == test_user.id,
            UserDevice.device_id == test_device.id
        ).first()
        assert deleted is None

    def test_unbind_nonexistent_binding(self, db_session, test_user, test_device):
        """测试解绑不存在的绑定关系抛出异常"""
        with pytest.raises(ValueError, match="绑定关系不存在"):
            unbind_user_device(db_session, test_user.id, test_device.id)
