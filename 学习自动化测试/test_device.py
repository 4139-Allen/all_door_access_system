import pytest

from 学习自动化测试.conftest import create_test_device

BASE_URL = "https://www.doorlink.top"

from test_utils.assert_util import assert_success, assert_failure

class TestDevice:

    @pytest.mark.smoke
    def test_admin_get_devices(self, admin_client):
        """管理员已登录查看设备列表"""
        resp = admin_client.get(f"{BASE_URL}/api/devices")
        data = assert_success(resp, expected_msg="获取设备列表成功")

    @pytest.mark.smoke
    def test_anon_get_devices(self, anon_client):
        """未登陆获取设备列表"""
        resp = anon_client.get(f"{BASE_URL}/api/devices")
        data = assert_failure(resp, 401, "未提供认证凭证")

    @pytest.mark.destructive
    def test_update_device_name(self, admin_client, create_test_device):
        """测试修改设备名字/编号"""
        resp = admin_client.put(f"{BASE_URL}/api/devices/{create_test_device}",
                                json={"name": "测试改设备名", "location": "测试地址"}
                                )
        assert_success(resp)

    @pytest.mark.destructive
    def test_update_device_name_location(self, admin_client, create_test_device):
        """测试修改设备名字和位置"""
        resp = admin_client.put(f"{BASE_URL}/api/devices/{create_test_device}",
                                json={"name": "测试改设备名", "location": "测试修改地址"}
                                )
        assert_success(resp)

    @pytest.mark.destructive
    def test_delete_device(self, admin_client, create_test_device):
        """测试删除设备"""






def test_health_check(admin_client):
    """测试系统健康"""
    resp = admin_client.get(f"{BASE_URL}/api/health")
    body = resp.json()

    print(f"\n{BASE_URL}/api/health")
    print(f"状态码：{resp.status_code}")
    print(f"响应体：{body}")

    assert resp.status_code == 200
    assert body["status"] == "healthy"







