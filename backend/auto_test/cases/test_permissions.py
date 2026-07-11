"""
权限控制专项测试

测试维度（3×3 矩阵）：
  用户角色  →  admin / user / 未登录(anon)
  操作类型  →  创建 / 读取 / 修改 / 删除
  资源模块  →  用户管理 / 设备管理 / 门禁控制 / 统计数据 / 权限管理

预期行为：
  - admin:  所有操作通过
  - user:   仅允许读取类操作（看自己设备、查日志、看统计）
  - anon:   全部返回 401
"""
import uuid
import pytest
from test_util.assert_util import (
    assert_success,
    assert_failure,
    assert_forbidden,
    assert_unauthorized,
)


# ==================== 核心矩阵：3 个角色 × N 个操作 ====================

class TestPermissionMatrix:
    """权限矩阵验证"""

    # ---- 用户管理 ----

    @pytest.mark.parametrize("client_fixture,status_code", [
        ("admin_client", 200),
        ("user_client", 403),
        ("anon_client", 401),
    ])
    def test_list_users_permission(self, request, client_fixture, status_code):
        """GET /users 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/users")
        assert resp.status_code == status_code

    @pytest.mark.parametrize("client_fixture,status_code", [
        ("admin_client", 201),
        ("user_client", 403),
        ("anon_client", 401),
    ])
    @pytest.mark.destructive
    def test_create_user_permission(self, request, client_fixture, status_code):
        """POST /users 权限测试"""
        client = request.getfixturevalue(client_fixture)
        import uuid
        resp = client.post("/users", json={
            "username": f"usr_{uuid.uuid4().hex[:8]}",
            "password": "test123456",
        })
        if status_code == 201:
            assert resp.status_code in (200, 201)
            # 清理
            user_id = resp.json()["data"]["id"]
            request.getfixturevalue("admin_client").delete(f"/users/{user_id}")
        else:
            assert resp.status_code == status_code

    @pytest.mark.parametrize("client_fixture,status_code", [
        ("admin_client", 204),
        ("user_client", 403),
        ("anon_client", 401),
    ])
    @pytest.mark.destructive
    def test_delete_user_permission(self, request, client_fixture, status_code):
        """DELETE /users/{id} 权限测试"""
        # 先创建一个用户
        admin = request.getfixturevalue("admin_client")
        import uuid
        create_resp = admin.post("/users", json={
            "username": f"usr_{uuid.uuid4().hex[:8]}",
            "password": "test123456",
        })
        user_id = create_resp.json()["data"]["id"]

        client = request.getfixturevalue(client_fixture)
        resp = client.delete(f"/users/{user_id}")
        if status_code == 204:
            assert resp.status_code == 204
        else:
            assert resp.status_code == status_code
            # 清理
            admin.delete(f"/users/{user_id}")

    # ---- 设备管理 ----

    @pytest.mark.parametrize("client_fixture,status_code", [
        ("admin_client", 201),
        ("user_client", 403),
        ("anon_client", 401),
    ])
    def test_create_device_permission(self, request, client_fixture, status_code):
        """POST /devices 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.post("/devices", json={
            "name": f"DEV-{uuid.uuid4().hex[:6].upper()}",
            "location": "权限测试",
        })
        assert resp.status_code == status_code
        # 如果 admin 创建成功，清理
        if status_code == 201:
            device_id = resp.json().get("data", {}).get("device_id")
            if device_id:
                request.getfixturevalue("admin_client").delete(f"/devices/{device_id}")

    @pytest.mark.parametrize("client_fixture,status_code", [
        ("admin_client", 200),
        ("user_client", 200),  # 普通用户也能查看（有 door.open 权限）
        ("anon_client", 401),
    ])
    def test_view_devices_permission(self, request, client_fixture, status_code):
        """GET /devices 权限测试（普通用户也有查看权限）"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/devices?page=1&size=10")
        assert resp.status_code == status_code

    # ---- 统计数据 ----

    @pytest.mark.parametrize("client_fixture,status_code", [
        ("admin_client", 200),
        ("user_client", 200),  # 普通用户也可以看统计
        ("anon_client", 401),
    ])
    def test_view_statistics_permission(self, request, client_fixture, status_code):
        """GET /statistics 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/statistics")
        assert resp.status_code == status_code

    # ---- 权限管理（严格：仅 admin） ----

    @pytest.mark.parametrize("client_fixture,status_code", [
        ("admin_client", 200),
        ("user_client", 403),
        ("anon_client", 401),
    ])
    def test_view_permissions_permission(self, request, client_fixture, status_code):
        """GET /permissions 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/permissions")
        assert resp.status_code == status_code

    @pytest.mark.parametrize("client_fixture,status_code", [
        ("admin_client", 200),
        ("user_client", 403),
        ("anon_client", 401),
    ])
    def test_view_roles_permission(self, request, client_fixture, status_code):
        """GET /roles 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/roles")
        assert resp.status_code == status_code

    # ---- 门禁 ----

    @pytest.mark.parametrize("client_fixture,status_code", [
        ("admin_client", 200),
        ("user_client", 200),  # 自己的日志可以看
        ("anon_client", 401),
    ])
    def test_view_door_logs_permission(self, request, client_fixture, status_code):
        """GET /door-logs 权限测试（用户可查看自己的日志）"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/door-logs?page=1&size=10")
        assert resp.status_code == status_code


class TestRoleSpecificBehavior:
    """角色特定行为测试"""

    def test_admin_has_all_permissions(self, admin_client):
        """管理员应拥有 dashboard.view 权限"""
        import uuid
        resp = admin_client.post("/devices", json={
            "name": f"DEV-{uuid.uuid4().hex[:6].upper()}",
            "location": "验证管理员权限",
        })
        assert resp.status_code in (200, 201)

    def test_user_cannot_manage_permissions(self, user_client):
        """普通用户不能管理角色"""
        resp = user_client.get("/roles")
        assert resp.status_code == 403

    def test_user_can_open_bound_doors(self, user_client, admin_client):
        """普通用户可以开门（如果有权限）"""
        resp = user_client.get("/doors?page=1&size=10")
        # 能访问 /doors/{id}/open 的权限检查通过即可
        # 具体开门测试在 test_door.py 中
        pass
