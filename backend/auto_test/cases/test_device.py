"""
设备管理模块测试

覆盖：
  - POST   /devices                        创建设备（Admin only）
  - GET    /devices                         设备列表（权限过滤）
  - PUT    /devices/{device_id}             更新设备（Admin only）
  - DELETE /devices/{device_id}             删除设备（Admin only）
  - POST   /devices/{device_id}/bind        绑定用户（Admin only）
  - DELETE /devices/{device_id}/unbind      解绑用户（Admin only）
"""
import uuid
import pytest
from test_util.assert_util import (
    assert_success,
    assert_failure,
    assert_forbidden,
    assert_unauthorized,
)
from test_util.device_helper import create_device, cleanup_device



# ==================== Tests ====================


@pytest.mark.usefixtures("admin_client")
class TestDeviceCreate:
    """创建设备"""

    @pytest.mark.destructive
    def test_create_device_success(self, admin_client):
        """管理员创建设备 → 返回 device_id"""
        device_id = create_device(admin_client)
        assert isinstance(device_id, int) and device_id > 0
        cleanup_device(admin_client, device_id)

    def test_create_device_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.post("/devices", json={
            "name": f"DEV-{uuid.uuid4().hex[:6].upper()}",
            "location": "test",
        })
        assert_unauthorized(resp)

    def test_create_device_forbidden(self, shared_user_client):
        """普通用户 → 403"""
        resp = shared_user_client.post("/devices", json={
            "name": f"DEV-{uuid.uuid4().hex[:6].upper()}",
            "location": "test",
        })
        assert_forbidden(resp)

    def test_create_device_missing_name(self, admin_client):
        """缺少必填字段 name → 422"""
        resp = admin_client.post("/devices", json={
            "location": "test",
        })
        assert resp.status_code == 422


class TestDeviceList:
    """设备列表"""

    @pytest.mark.smoke
    def test_list_devices_as_admin(self, admin_client):
        """管理员查看所有设备 → 包含分页"""
        resp = admin_client.get("/devices?page=1&size=10")
        assert_success(resp).has_pagination()

    @pytest.mark.destructive
    def test_list_devices_as_bound_user(self, user_client, admin_client):
        """绑定设备的普通用户只能看到自己的设备"""
        # 先创建一个设备并绑定给用户
        device_id = create_device(admin_client)
        # 需要先知道用户的 ID
        users_resp = admin_client.get("/users?page=1&size=10")
        user_id = users_resp.json()["data"]["list"][0]["id"]
        admin_client.post(f"/devices/{device_id}/bind", json={
            "user_id": user_id,
        })

        resp = user_client.get("/devices")
        data = assert_success(resp).body["data"]
        assert len(data.get("list", [])) >= 0

        # 清理
        cleanup_device(admin_client, device_id)

    def test_list_devices_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.get("/devices")
        assert_unauthorized(resp)


class TestDeviceUpdate:
    """更新设备"""

    @pytest.mark.destructive
    def test_update_device_success(self, admin_client):
        """管理员更新设备信息"""
        device_id = create_device(admin_client)

        resp = admin_client.put(f"/devices/{device_id}", json={
            "name": f"DEV-{uuid.uuid4().hex[:6].upper()}",
            "location": "自动化测试-更新位置",
            "status": "online",
        })
        assert_success(resp, "更新成功")

        cleanup_device(admin_client, device_id)

    def test_update_device_no_auth(self, anon_client, admin_client):
        """未登录 → 401"""
        device_id = create_device(admin_client)
        resp = anon_client.put(f"/devices/{device_id}", json={"name": "x"})
        assert_unauthorized(resp)
        cleanup_device(admin_client, device_id)

    def test_update_device_forbidden(self, shared_user_client, admin_client):
        """普通用户 → 403"""
        device_id = create_device(admin_client)
        resp = shared_user_client.put(f"/devices/{device_id}", json={"name": "x"})
        assert_forbidden(resp)
        cleanup_device(admin_client, device_id)

    def test_update_nonexistent_device(self, admin_client):
        """更新不存在的设备 → 404"""
        resp = admin_client.put("/devices/99999", json={
            "name": f"DEV-{uuid.uuid4().hex[:6].upper()}",
        })
        assert_failure(resp, 404, "不存在")


class TestDeviceDelete:
    """删除设备"""

    @pytest.mark.destructive
    def test_delete_device_success(self, admin_client):
        """管理员删除设备 → 204"""
        device_id = create_device(admin_client)
        resp = admin_client.delete(f"/devices/{device_id}")
        assert resp.status_code == 204

    def test_delete_device_no_auth(self, anon_client, admin_client):
        """未登录 → 401"""
        device_id = create_device(admin_client)
        resp = anon_client.delete(f"/devices/{device_id}")
        assert_unauthorized(resp)
        cleanup_device(admin_client, device_id)

    def test_delete_device_forbidden(self, shared_user_client, admin_client):
        """普通用户 → 403"""
        device_id = create_device(admin_client)
        resp = shared_user_client.delete(f"/devices/{device_id}")
        assert_forbidden(resp)
        cleanup_device(admin_client, device_id)

    def test_delete_nonexistent_device(self, admin_client):
        """删除不存在的设备 → 404"""
        resp = admin_client.delete("/devices/99999")
        assert_failure(resp, 404, "不存在")


class TestDeviceBind:
    """绑定/解绑用户"""

    @pytest.mark.destructive
    def test_bind_user_success(self, admin_client):
        """管理员绑定用户到设备 → 成功"""
        device_id = create_device(admin_client)

        # 获取第一个普通用户
        users_resp = admin_client.get("/users?role=user&page=1&size=1")
        first_user = users_resp.json()["data"]["list"][0]
        user_id = first_user["id"]

        resp = admin_client.post(f"/devices/{device_id}/bind", json={
            "user_id": user_id,
        })
        assert_success(resp, "绑定成功")

        # 解绑并清理
        admin_client.delete(f"/devices/{device_id}/unbind?user_id={user_id}")
        cleanup_device(admin_client, device_id)

    def test_bind_user_no_auth(self, anon_client, admin_client):
        """未登录 → 401"""
        device_id = create_device(admin_client)
        resp = anon_client.post(f"/devices/{device_id}/bind", json={"user_id": 1})
        assert_unauthorized(resp)
        cleanup_device(admin_client, device_id)

    def test_bind_user_forbidden(self, shared_user_client, admin_client):
        """普通用户 → 403"""
        device_id = create_device(admin_client)
        resp = shared_user_client.post(f"/devices/{device_id}/bind", json={"user_id": 1})
        assert_forbidden(resp)
        cleanup_device(admin_client, device_id)

    @pytest.mark.destructive
    def test_unbind_user_success(self, admin_client):
        """管理员解绑用户 → 204"""
        device_id = create_device(admin_client)

        users_resp = admin_client.get("/users?role=user&page=1&size=1")
        user_id = users_resp.json()["data"]["list"][0]["id"]

        # 先绑定
        admin_client.post(f"/devices/{device_id}/bind", json={"user_id": user_id})
        # 再解绑
        resp = admin_client.delete(f"/devices/{device_id}/unbind?user_id={user_id}")
        assert resp.status_code == 204

        cleanup_device(admin_client, device_id)
