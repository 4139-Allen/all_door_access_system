"""
登录 API 集成测试
测试 /api/auth/login 接口的完整流程
"""
import pytest


class TestLoginAPI:
    """用户登录 API 测试"""

    def test_login_success(self, client, test_user):
        """测试登录成功：完整走通 路由→校验→查库→验密→签发 token→返回"""
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpass123"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "authorization" in response.headers
        assert response.headers["authorization"].startswith("Bearer ")

    def test_login_failure_wrong_password(self, client, test_user):
        """测试登录失败：密码错误"""
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "wrongpass"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "密码错误" in data.get("msg", "")

    def test_login_with_nonexistent_user(self, client):
        """测试登录失败：用户不存在"""
        response = client.post("/api/auth/login", json={
            "username": "nonexistent",
            "password": "testpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "用户不存在" in data.get("msg", "")

    def test_login_with_empty_username(self, client):
        """测试登录失败：用户名为空"""
        response = client.post("/api/auth/login", json={
            "username": "",
            "password": "testpass123"
        })
        assert response.status_code in [200, 422]

    def test_login_with_empty_password(self, client):
        """测试登录失败：密码为空"""
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": ""
        })
        assert response.status_code in [200, 422]
