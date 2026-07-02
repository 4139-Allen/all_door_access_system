"""
权限验证测试（API 层）
测试角色权限控制、Token 校验等
"""
import pytest


class TestPermissionValidation:
    """权限验证测试"""

    def test_user_cannot_access_admin_endpoints(self, client, auth_headers):
        """测试普通用户无法访问管理员端点"""
        # 尝试获取用户列表
        response = client.get("/api/users", headers=auth_headers)
        assert response.status_code == 403

        # 尝试创建设备
        response = client.post("/api/devices", json={
            "name": "test",
            "location": "test"
        }, headers=auth_headers)
        assert response.status_code == 403

        # 尝试删除用户
        response = client.delete("/api/users/1", headers=auth_headers)
        assert response.status_code == 403

    def test_user_can_only_access_own_data(self, client, auth_headers, test_user, db_session):
        """测试普通用户只能访问自己的数据"""
        from database.models.user import User
        from utils.auth import hash_password

        # 创建另一个用户
        other_user = User(username="otheruser", password=hash_password("otherpass"), role="user")
        db_session.add(other_user)
        db_session.commit()

        # 尝试查询其他用户的设备（应该被拒绝）
        response = client.get(f"/api/users/{other_user.id}/devices", headers=auth_headers)
        assert response.status_code == 403

    def test_admin_can_access_all_endpoints(self, client, admin_headers):
        """测试管理员可以访问所有端点"""
        # 获取用户列表
        response = client.get("/api/users", headers=admin_headers)
        assert response.status_code == 200

        # 创建设备
        response = client.post("/api/devices", json={
            "name": "admin_test",
            "location": "test"
        }, headers=admin_headers)
        assert response.status_code == 200


class TestHealthCheck:
    """健康检查测试"""

    def test_health_check_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
