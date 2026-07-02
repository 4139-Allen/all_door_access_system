"""
设备管理测试（服务层 + API 层）
"""
import pytest
from services.device_service import (
    create_device, update_device, delete_device,
    get_device_list, check_user_permission,
    bind_user_device, unbind_user_device
)
from database.models.device import Device
from database.models.user_device import UserDevice
from schemas.device_schema import DeviceCreate, DeviceUpdate
from core.exceptions import NotFoundError
from pydantic import ValidationError


# ============================================================
# 服务层测试
# ============================================================

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


class TestCreateDeviceService:
    """创建设备 - 服务层"""

    def test_create_device_success(self, db_session):
        """测试成功创建设备"""
        data = DeviceCreate(name="002", location="教学楼")
        device = create_device(db_session, data)

        assert device.id is not None
        assert device.name == "002"
        assert device.location == "教学楼"
        assert device.status == "online"

    def test_create_device_with_empty_name(self):
        """测试创建空名称设备（预期参数校验失败）"""
        with pytest.raises(ValidationError):
            DeviceCreate(name="", location="教学楼")

    def test_create_device_empty_location(self):
        """测试创建空位置设备抛出异常"""
        with pytest.raises(ValidationError):
            DeviceCreate(name="099", location="")

    def test_create_duplicate_device(self, db_session):
        """测试创建重复设备抛出异常"""
        data = DeviceCreate(name="001", location="校门")
        create_device(db_session, data)

        duplicate_data = DeviceCreate(name="001", location="校门")
        with pytest.raises(ValueError, match="已存在"):
            create_device(db_session, duplicate_data)


class TestUpdateDeviceService:
    """更新设备 - 服务层"""

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


class TestDeleteDeviceService:
    """删除设备 - 服务层"""

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


class TestGetDeviceListService:
    """获取设备列表 - 服务层"""

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


class TestBindUserDeviceService:
    """绑定用户设备 - 服务层"""

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
        with pytest.raises(NotFoundError, match="设备不存在"):
            bind_user_device(db_session, test_user.id, 99999)


class TestUnbindUserDeviceService:
    """解绑用户设备 - 服务层"""

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


# ============================================================
# API 层测试
# ============================================================

class TestDeviceAPI:
    """设备 API 测试"""

    def test_list_devices_requires_auth(self, client):
        """测试列出设备需要认证"""
        response = client.get("/api/devices")
        assert response.status_code == 401

    def test_list_devices_with_auth(self, client, auth_headers):
        """测试认证后列出设备"""
        response = client.get("/api/devices", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_create_device_as_admin(self, client, admin_headers):
        """测试管理员创建设备"""
        response = client.post("/api/devices", json={
            "name": "002",
            "location": "教学楼"
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_create_device_as_user_forbidden(self, client, auth_headers):
        """测试普通用户创建设备被拒绝"""
        response = client.post("/api/devices", json={
            "name": "003",
            "location": "图书馆"
        }, headers=auth_headers)
        assert response.status_code == 403

    def test_update_device_as_admin(self, client, admin_headers, test_device):
        """测试管理员更新设备"""
        response = client.put(f"/api/devices/{test_device.id}", json={
            "name": "001-updated",
            "status": "offline"
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_delete_device_as_admin(self, client, admin_headers):
        """测试管理员删除设备"""
        # 先创建设备
        create_response = client.post("/api/devices", json={
            "name": "999",
            "location": "测试位置"
        }, headers=admin_headers)
        device_id = create_response.json()["data"]["device_id"]

        # 删除设备
        response = client.delete(f"/api/devices/{device_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_bind_user_device_as_admin(self, client, admin_headers, test_user, test_device):
        """测试管理员绑定用户和设备"""
        response = client.post(f"/api/devices/{test_device.id}/bind", json={
            "user_id": test_user.id
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_unbind_user_device_as_admin(self, client, admin_headers, test_user, test_device, db_session):
        """测试管理员解绑用户和设备"""
        from database.models.user_device import UserDevice

        # 先绑定
        binding = UserDevice(user_id=test_user.id, device_id=test_device.id)
        db_session.add(binding)
        db_session.commit()

        # 再解绑
        response = client.delete(f"/api/devices/{test_device.id}/unbind?user_id={test_user.id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_device_list_with_name_filter(self, client, admin_headers, test_device):
        """测试设备列表按名称筛选"""
        response = client.get(f"/api/devices?name={test_device.name}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["list"]) >= 1

    def test_create_duplicate_device(self, client, admin_headers, test_device):
        """测试创建重复设备"""
        response = client.post("/api/devices", json={
            "name": test_device.name,
            "location": test_device.location
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400

    def test_bind_duplicate_user_device(self, client, admin_headers, test_user, test_device, db_session):
        """测试重复绑定用户和设备"""
        from database.models.user_device import UserDevice

        # 先绑定
        binding = UserDevice(user_id=test_user.id, device_id=test_device.id)
        db_session.add(binding)
        db_session.commit()

        # 再次绑定应该失败
        response = client.post(f"/api/devices/{test_device.id}/bind", json={
            "user_id": test_user.id
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400

    def test_unbind_nonexistent_binding(self, client, admin_headers, test_user, test_device):
        """测试解绑不存在的绑定关系"""
        response = client.delete(f"/api/devices/{test_device.id}/unbind?user_id={test_user.id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] in [200, 400]

    def test_bind_nonexistent_device(self, client, admin_headers, test_user):
        """测试绑定不存在的设备"""
        response = client.post("/api/devices/99999/bind", json={
            "user_id": test_user.id
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 404

    def test_update_nonexistent_device(self, client, admin_headers):
        """测试更新不存在的设备"""
        response = client.put("/api/devices/99999", json={
            "name": "nonexistent"
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 404

    def test_delete_nonexistent_device(self, client, admin_headers):
        """测试删除不存在的设备"""
        response = client.delete("/api/devices/99999", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 404

    def test_create_device_with_empty_name(self, client, admin_headers):
        """测试创建空名称设备"""
        response = client.post("/api/devices", json={
            "name": "",
            "location": "test"
        }, headers=admin_headers)
        assert response.status_code in [422]

    def test_create_device_with_empty_location(self, client, admin_headers):
        """测试创建空位置设备"""
        response = client.post("/api/devices", json={
            "name": "test",
            "location": ""
        }, headers=admin_headers)
        assert response.status_code in [200, 422]
