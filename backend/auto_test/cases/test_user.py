"""
用户管理模块测试

覆盖：
  - GET  /users                  用户列表（分页、筛选）
  - POST /users                  创建用户
  - DELETE /users/{user_id}      删除用户
  - GET  /users/{user_id}/devices 用户绑定的设备列表
  - PUT  /users/{user_id}/role   修改用户角色
  - POST /auth/register          注册
"""
import uuid
import pytest
from test_util.assert_util import (
    assert_success,
    assert_failure,
    assert_forbidden,
    assert_created,
    assert_unauthorized,
)


class TestUserList:
    """用户列表查询"""

    @pytest.mark.smoke
    def test_list_users_as_admin(self, admin_client):
        """管理员查看用户列表 → 分页数据"""
        resp = admin_client.get("/users?page=1&size=10")
        assert_success(resp) \
            .has_pagination() \
            .field_type("total", int)

    def test_list_users_filter_by_role(self, admin_client):
        """按角色筛选用户"""
        resp = admin_client.get("/users?role=admin")
        data = assert_success(resp).body["data"]
        assert data["total"] >= 1
        for user in data["list"]:
            assert user["role"] == "admin"

    def test_list_users_filter_by_username(self, admin_client):
        """按用户名模糊搜索"""
        resp = admin_client.get("/users?username=admin")
        data = assert_success(resp).body["data"]
        assert len(data["list"]) >= 1
        assert "admin" in data["list"][0]["username"].lower()

    def test_list_users_unauthorized(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.get("/users")
        assert_unauthorized(resp)

    def test_list_users_forbidden_for_regular_user(self, user_client):
        """普通用户无查看用户列表权限 → 403"""
        resp = user_client.get("/users")
        assert_forbidden(resp)


class TestUserCreate:
    """创建用户"""

    @pytest.mark.destructive
    def test_create_user_success(self, admin_client):
        """管理员创建用户 → 201"""
        name = f"usr_{uuid.uuid4().hex[:8]}"
        resp = admin_client.post("/users", json={
            "username": name,
            "password": "test123456",
        })
        assert_created(resp)
        data = resp.json()["data"]
        assert data["username"] == name
        assert data["role"] == "user"

        # 清理
        admin_client.delete(f"/users/{data['id']}")

    def test_create_user_duplicate(self, admin_client):
        """创建重复用户名 → 400"""
        name = f"dup_{uuid.uuid4().hex[:8]}"
        admin_client.post("/users", json={
            "username": name,
            "password": "test123456",
        })
        resp = admin_client.post("/users", json={
            "username": name,
            "password": "test123456",
        })
        assert_failure(resp, 400, "已存在")

    def test_create_user_no_auth(self, anon_client):
        """未登录创建用户 → 401"""
        resp = anon_client.post("/users", json={
            "username": f"usr_{uuid.uuid4().hex[:8]}",
            "password": "test123456",
        })
        assert_unauthorized(resp)

    def test_create_user_forbidden(self, user_client):
        """普通用户创建用户 → 403"""
        resp = user_client.post("/users", json={
            "username": f"usr_{uuid.uuid4().hex[:8]}",
            "password": "test123456",
        })
        assert_forbidden(resp)

    def test_create_user_invalid_username(self, admin_client):
        """用户名含特殊字符 → 422"""
        resp = admin_client.post("/users", json={
            "username": "invalid@user!",
            "password": "test123456",
        })
        assert resp.status_code == 422


class TestUserDelete:
    """删除用户"""

    @pytest.mark.destructive
    def test_delete_user_success(self, admin_client):
        """管理员删除用户 → 204"""
        name = f"usr_{uuid.uuid4().hex[:8]}"
        create_resp = admin_client.post("/users", json={
            "username": name,
            "password": "test123456",
        })
        user_id = create_resp.json()["data"]["id"]

        resp = admin_client.delete(f"/users/{user_id}")
        assert resp.status_code == 204

    def test_delete_nonexistent_user(self, admin_client):
        """删除不存在的用户 → 404"""
        resp = admin_client.delete("/users/99999")
        assert_failure(resp, 404, "不存在")

    def test_delete_user_no_auth(self, anon_client):
        """未登录删除用户 → 401"""
        resp = anon_client.delete("/users/1")
        assert_unauthorized(resp)

    def test_delete_user_forbidden(self, user_client):
        """普通用户删除用户 → 403"""
        resp = user_client.delete("/users/1")
        assert_forbidden(resp)


class TestUserRole:
    """修改用户角色"""

    @pytest.mark.destructive
    def test_update_role_success(self, admin_client):
        """管理员修改用户角色"""
        name = f"usr_{uuid.uuid4().hex[:8]}"
        create_resp = admin_client.post("/users", json={
            "username": name,
            "password": "test123456",
        })
        user_id = create_resp.json()["data"]["id"]

        resp = admin_client.put(f"/users/{user_id}/role", json={
            "role": "operator",
        })
        assert_success(resp, "角色修改成功")

        # 清理
        admin_client.delete(f"/users/{user_id}")

    def test_update_role_invalid(self, admin_client):
        """设置不存在的角色 → 400"""
        resp = admin_client.put("/users/1/role", json={
            "role": "nonexistent_role_xxx",
        })
        assert_failure(resp, 400)


class TestUserDevices:
    """用户设备绑定查询"""

    def test_get_user_devices_as_admin(self, admin_client):
        """管理员查看用户的设备列表"""
        resp = admin_client.get("/users/1/devices")
        assert_success(resp)
        resp.json()["data"]  # 空列表也合法

    def test_get_user_devices_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.get("/users/1/devices")
        assert_unauthorized(resp)

    def test_get_user_devices_forbidden(self, user_client):
        """普通用户无权查看其他用户的设备 → 403"""
        resp = user_client.get("/users/1/devices")
        assert_forbidden(resp)
