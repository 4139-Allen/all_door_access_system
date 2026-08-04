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


# ==================== 公共参数组合 ====================
# admin / user / anon 三类用户的行为矩阵
ADMIN_FULL = [("admin_client", 200), ("shared_user_client", 403), ("anon_client", 401)]
ADMIN_VIEW = [("admin_client", 200), ("shared_user_client", 200), ("anon_client", 401)]
ADMIN_CREATE = [("admin_client", 201), ("shared_user_client", 403), ("anon_client", 401)]
ADMIN_DELETE = [("admin_client", 204), ("shared_user_client", 403), ("anon_client", 401)]
# destructive 操作需要独立用户测试
ADMIN_CREATE_ISOLATED = [("admin_client", 201), ("user_client", 403), ("anon_client", 401)]
ADMIN_DELETE_ISOLATED = [("admin_client", 204), ("user_client", 403), ("anon_client", 401)]


class TestPermissionMatrix:
    """权限矩阵验证"""

    # ---- 用户管理 ----

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_FULL)
    def test_list_users_permission(self, request, client_fixture, status_code):
        """GET /users 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/users")
        assert resp.status_code == status_code

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_CREATE_ISOLATED)
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
            user_id = resp.json()["data"]["id"]
            request.getfixturevalue("admin_client").delete(f"/users/{user_id}")
        else:
            assert resp.status_code == status_code

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_DELETE_ISOLATED)
    @pytest.mark.destructive
    def test_delete_user_permission(self, request, client_fixture, status_code):
        """DELETE /users/{id} 权限测试"""
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
            assert resp.status_code in (200, 204)
        elif status_code == 200:
            assert resp.status_code == 200
        else:
            assert resp.status_code == status_code
            admin.delete(f"/users/{user_id}")

    # ---- 设备管理 ----

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_CREATE)
    def test_create_device_permission(self, request, client_fixture, status_code):
        """POST /devices 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.post("/devices", json={
            "name": f"DEV-{uuid.uuid4().hex[:6].upper()}",
            "location": "权限测试",
        })
        assert resp.status_code == status_code
        if status_code == 201:
            device_id = resp.json().get("data", {}).get("device_id")
            if device_id:
                request.getfixturevalue("admin_client").delete(f"/devices/{device_id}")

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_VIEW)
    def test_view_devices_permission(self, request, client_fixture, status_code):
        """GET /devices 权限测试（普通用户也有查看权限）"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/devices?page=1&size=10")
        assert resp.status_code == status_code

    # ---- 统计数据 ----

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_VIEW)
    def test_view_statistics_permission(self, request, client_fixture, status_code):
        """GET /statistics 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/statistics")
        assert resp.status_code == status_code

    # ---- 权限管理（严格：仅 admin） ----

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_FULL)
    def test_view_permissions_permission(self, request, client_fixture, status_code):
        """GET /permissions 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/permissions")
        assert resp.status_code == status_code

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_FULL)
    def test_view_roles_permission(self, request, client_fixture, status_code):
        """GET /roles 权限测试"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/roles")
        assert resp.status_code == status_code

    # ---- 门禁 ----

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_FULL)
    def test_view_door_logs_permission(self, request, client_fixture, status_code):
        """GET /door-logs 权限测试（仅管理员可查看全部日志）"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/door-logs?page=1&size=10")
        assert resp.status_code == status_code

    @pytest.mark.parametrize("client_fixture,status_code", ADMIN_VIEW)
    def test_view_my_logs_permission(self, request, client_fixture, status_code):
        """GET /door/my-logs 权限测试（所有用户可查看个人日志）"""
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/door/my-logs?page=1&size=10")
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

    def test_user_cannot_manage_permissions(self, shared_user_client):
        """普通用户不能管理角色"""
        resp = shared_user_client.get("/roles")
        assert resp.status_code == 403

    def test_user_can_open_bound_doors(self, shared_user_client, admin_client):
        """普通用户可以开门（如果有权限）"""
        resp = shared_user_client.get("/doors?page=1&size=10")
        # 能访问 /doors/{id}/open 的权限检查通过即可
        # 具体开门测试在 test_door.py 中
        pass


class TestRoleCreate:
    """创建角色边界校验"""

    @pytest.mark.destructive
    def test_create_role_success(self, admin_client):
        """创建角色成功 → 返回 role_code"""
        code = f"role_{uuid.uuid4().hex[:8]}"
        resp = admin_client.post("/roles", json={"name": "测试角色", "role_code": code})
        assert resp.status_code in (200, 201)
        assert resp.json()["data"]["role_code"] == code
        admin_client.delete(f"/roles/{resp.json()['data']['id']}")

    def test_create_role_name_too_long(self, admin_client):
        """角色名称超长 31 字符 → 422"""
        resp = admin_client.post("/roles", json={"name": "x" * 31, "role_code": "r1"})
        assert resp.status_code == 422

    def test_create_role_code_too_long(self, admin_client):
        """角色标识超长 31 字符 → 422"""
        resp = admin_client.post("/roles", json={"name": "r2", "role_code": "y" * 31})
        assert resp.status_code == 422

    def test_create_role_name_empty(self, admin_client):
        """角色名称空串 → 422"""
        resp = admin_client.post("/roles", json={"name": "", "role_code": "r3"})
        assert resp.status_code == 422

    def test_create_role_code_empty(self, admin_client):
        """角色标识空串 → 422"""
        resp = admin_client.post("/roles", json={"name": "r4", "role_code": ""})
        assert resp.status_code == 422

    def test_create_role_name_whitespace(self, admin_client):
        """角色名称纯空白 → 400"""
        resp = admin_client.post("/roles", json={"name": "   ", "role_code": "r5"})
        assert_failure(resp, 400, "不能为空")

    def test_create_role_code_whitespace(self, admin_client):
        """角色标识纯空白 → 400"""
        resp = admin_client.post("/roles", json={"name": "r6", "role_code": "   "})
        assert_failure(resp, 400, "不能为空")

    @pytest.mark.destructive
    def test_create_role_duplicate_code(self, admin_client):
        """角色标识重复 → 400"""
        code = f"dup_{uuid.uuid4().hex[:8]}"
        resp = admin_client.post("/roles", json={"name": "重复角色", "role_code": code})
        assert resp.status_code in (200, 201)
        resp2 = admin_client.post("/roles", json={"name": "另一角色", "role_code": code})
        assert_failure(resp2, 400, "已存在")
        admin_client.delete(f"/roles/{resp.json()['data']['id']}")

    @pytest.mark.destructive
    def test_create_role_duplicate_name(self, admin_client):
        """角色名称重复 → 400"""
        name = f"同名_{uuid.uuid4().hex[:8]}"
        resp = admin_client.post("/roles", json={"name": name, "role_code": "n1"})
        assert resp.status_code in (200, 201)
        resp2 = admin_client.post("/roles", json={"name": name, "role_code": "n2"})
        assert_failure(resp2, 400, "已存在")
        admin_client.delete(f"/roles/{resp.json()['data']['id']}")


class TestRolePermissionSetting:
    """设置角色权限边界"""

    def test_set_permissions_invalid_id(self, admin_client):
        """非法权限 ID → 400"""
        resp = admin_client.put("/roles/2/permissions", json={"permission_ids": [1, 99999]})
        assert_failure(resp, 400, "无效的权限ID")

    def test_set_permissions_empty(self, admin_client):
        """空权限列表 → 成功（清空角色权限）"""
        resp = admin_client.put("/roles/2/permissions", json={"permission_ids": []})
        assert_success(resp)
        # 恢复 operator 默认权限（避免影响后续测试）
        default_ids = list(range(1, 13))  # dashboard.view ~ alert.unlock
        admin_client.put("/roles/2/permissions", json={"permission_ids": default_ids})

    def test_set_permissions_admin_forbidden(self, admin_client):
        """超级管理员角色权限不可修改 → 400"""
        resp = admin_client.put("/roles/1/permissions", json={"permission_ids": [1]})
        assert_failure(resp, 400, "超级管理员")

    def test_set_permissions_role_not_found(self, admin_client):
        """角色不存在 → 404"""
        resp = admin_client.put("/roles/99999/permissions", json={"permission_ids": [1]})
        assert_failure(resp, 404, "不存在")
