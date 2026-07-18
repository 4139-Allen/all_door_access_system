
import pytest
import requests
import json

from adodbapi.ado_consts import adNumeric

BASE_URL = "https://www.doorlink.top"

# ===============Fixture========================


@pytest.fixture(scope="session")
def client():
    """未登录的 HTTP 客户端"""
    return requests.session()


@pytest.fixture(scope="session")
def admin_client(client):
    resp = client.post(
        f"{BASE_URL}/api/auth/login",
        json={"username":"admin","password":"123456"}
    )
    token = resp.headers.get("Authorization", "").replace("Bearer ", "")
    client.headers.update({"Authorization":f"Bearer {token}"})
    return client

@pytest.fixture(scope="session")
def anon_client():
    """未登录的客户端（专门测试未认证场景）"""
    return requests.session()


@pytest.fixture
def register_user(admin_client, anon_client):
    """创建一个测试用户，测试完后admin删除"""
    import uuid
    name = f"test-user-{uuid.uuid4().hex[:6]}"
    resp = anon_client.post(
        f"{BASE_URL}/api/auth/register",
        json={"name":name, "password":}
    )


#===============设备=================
@pytest.fixture
def create_test_device(admin_client):
    """创建一个临时设备，测试完后自动删除"""
    import uuid
    name = f"test-device-{uuid.uuid4().hex[:6]}"
    resp = admin_client.post(
        f"{BASE_URL}/api/devices",
        json={"name":name, "location": "测试地址"}
    )
    device_id = resp.json()["data"]["device_id"]

    yield device_id     # 把设备 ID 交给测试用例

    #删除测试设备，保持环境干净
    resp_del = admin_client.delete(f"{BASE_URL}/api/devices/{device_id}")  #清理测试设备

    assert resp_del.status_code ==204



