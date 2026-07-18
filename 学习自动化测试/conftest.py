
import pytest
import requests
import json

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



