"""
门禁控制与日志模块测试

覆盖：
  - POST /doors/{device_id}/open   开门（权限校验、记录日志）
  - GET  /door-logs                日志查询（分页、过滤、权限）
"""
import uuid
import pytest
from test_util.assert_util import (
    assert_success,
    assert_failure,
    assert_forbidden,
    assert_unauthorized,
)


# ==================== Helpers ====================

def _prepare_bound_device(admin_client, user_id: int) -> int:
    """创建设备并绑定给指定用户，返回 device_id"""
    resp = admin_client.post("/devices", json={
        "name": f"DOOR-{uuid.uuid4().hex[:6].upper()}",
        "location": "自动化测试-门禁",
    })
    device_id = resp.json()["data"]["device_id"]
    admin_client.post(f"/devices/{device_id}/bind", json={"user_id": user_id})
    # 设备默认 offline，开门需要设为 online
    admin_client.put(f"/devices/{device_id}", json={"status": "online"})
    return device_id


def _cleanup_device(admin_client, device_id: int, user_id: int = None):
    """清理设备和绑定关系"""
    if user_id:
        admin_client.delete(f"/devices/{device_id}/unbind?user_id={user_id}")
    admin_client.delete(f"/devices/{device_id}")


# ==================== Tests ====================


class TestDoorOpen:
    """开门控制"""

    @pytest.mark.smoke
    @pytest.mark.destructive
    @pytest.mark.skip(reason="开门需要真实 MQTT 设备在线，测试环境无硬件")
    def test_admin_open_door_bound(self, admin_client):
        """管理员开门（管理员有全局权限）"""
        user_id = 1
        device_id = _prepare_bound_device(admin_client, user_id)
        resp = admin_client.post(f"/doors/{device_id}/open")
        assert_success(resp)
        _cleanup_device(admin_client, device_id, user_id)

    @pytest.mark.destructive
    @pytest.mark.skip(reason="开门需要真实 MQTT 设备在线，测试环境无硬件")
    def test_user_open_door_bound(self, user_client, admin_client):
        """绑定用户开门 → 成功"""
        users_resp = admin_client.get("/users?page=1&size=10")
        user_list = users_resp.json()["data"]["list"]
        if not user_list:
            pytest.skip("没有可用用户")
        first_user = user_list[0]
        user_id = first_user["id"]
        device_id = _prepare_bound_device(admin_client, user_id)
        resp = user_client.post(f"/doors/{device_id}/open")
        assert_success(resp)
        _cleanup_device(admin_client, device_id, user_id)

    @pytest.mark.destructive
    @pytest.mark.skip(reason="开门需要真实 MQTT 设备在线，测试环境无硬件")
    def test_user_open_door_not_bound(self, user_client, admin_client):
        """未绑定用户开门 → 403"""
        device_id = _prepare_bound_device(admin_client, user_id=1)
        resp = user_client.post(f"/doors/{device_id}/open")
        assert_forbidden(resp)
        _cleanup_device(admin_client, device_id, user_id=1)

    def test_open_door_no_auth(self, anon_client):
        """未登录开门 → 401"""
        resp = anon_client.post("/doors/1/open")
        assert_unauthorized(resp)

    def test_open_nonexistent_door(self, admin_client):
        """开启不存在的设备 → 404"""
        resp = admin_client.post("/doors/99999/open")
        assert_failure(resp, 404, "不存在")


class TestDoorLogs:
    """开门日志查询"""

    @pytest.mark.smoke
    def test_get_logs_as_admin(self, admin_client):
        """管理员查看所有日志 → 分页数据"""
        resp = admin_client.get(
            "/door-logs?page=1&size=10"
        )
        assert_success(resp).has_pagination()

    @pytest.mark.smoke
    def test_get_logs_as_user(self, user_client):
        """普通用户查看日志（只能看到自己的）"""
        resp = user_client.get(
            "/door-logs?page=1&size=10"
        )
        assert_success(resp).has_pagination()

    def test_get_logs_filter_by_device(self, admin_client):
        """按设备名过滤日志"""
        resp = admin_client.get("/door-logs?device_name=DEV&page=1&size=10")
        assert_success(resp).has_pagination()

    def test_get_logs_filter_by_status(self, admin_client):
        """按状态过滤日志"""
        resp = admin_client.get("/door-logs?status=成功&page=1&size=10")
        assert_success(resp).has_pagination()

    def test_get_logs_filter_by_date(self, admin_client):
        """按日期范围过滤日志"""
        resp = admin_client.get(
            "/door-logs?start_time=2026-01-01&end_time=2026-12-31&page=1&size=10"
        )
        assert_success(resp).has_pagination()

    def test_get_logs_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.get("/door-logs?page=1&size=10")
        assert_unauthorized(resp)

    def test_get_logs_invalid_date(self, admin_client):
        """无效日期格式 → 422 或 400"""
        resp = admin_client.get(
            "/door-logs?start_time=not-a-date&page=1&size=10"
        )
        assert resp.status_code in (400, 422)
