"""
用户管理测试（服务层 + API 层）
服务层：直接调用 service 函数，精确验证业务逻辑
API 层：通过 TestClient 调用 HTTP 接口，验证完整请求响应
"""
import pytest
from services.admin_user_service import login_user, db_create_user, delete_user_by_id, change_user_password
from database.models.user import User
from utils.auth import hash_password, verify_password
from core.exceptions import NotFoundError


# ============================================================
# 服务层测试
# ============================================================

class TestLoginUserService:
    """用户登录 - 服务层"""

    def test_login_with_correct_credentials(self, db_session, test_user):
        """测试使用正确的凭据登录"""
        result = login_user(db_session, "testuser", "testpass123")

        assert "token" in result
        assert result["role"] == "user"
        assert result["username"] == "testuser"

    def test_login_with_wrong_password(self, db_session, test_user):
        """测试使用错误的密码登录"""
        with pytest.raises(ValueError, match="密码错误"):
            login_user(db_session, "testuser", "wrongpass")

    def test_login_with_nonexistent_user(self, db_session):
        """测试使用不存在的用户名登录"""
        with pytest.raises(ValueError, match="用户不存在"):
            login_user(db_session, "nonexistent", "testpass123")


class TestCreateUserService:
    """用户创建 - 服务层"""

    def test_create_user_success(self, db_session):
        """测试成功创建用户"""
        user = db_create_user(db_session, "newuser", "newpass123", "user")

        assert user.id is not None
        assert user.username == "newuser"
        assert user.role == "user"
        assert verify_password("newpass123", user.password)

    def test_create_admin_user(self, db_session):
        """测试创建管理员用户"""
        user = db_create_user(db_session, "newadmin", "adminpass123", "admin")

        assert user.role == "admin"

    def test_create_duplicate_user(self, db_session, test_user):
        """测试创建重复用户名抛出异常"""
        with pytest.raises(ValueError, match="已存在"):
            db_create_user(db_session, "testuser", "anotherpass", "user")


class TestDeleteUserService:
    """用户删除 - 服务层"""

    def test_delete_user_success(self, db_session, test_user, test_admin):
        """测试成功删除用户"""
        result = delete_user_by_id(db_session, test_user.id, test_admin)

        assert result is True

        # 验证用户已被删除
        deleted_user = db_session.query(User).filter(User.id == test_user.id).first()
        assert deleted_user is None

    def test_delete_nonexistent_user(self, db_session, test_admin):
        """测试删除不存在的用户抛出异常"""
        with pytest.raises(NotFoundError, match="用户不存在"):
            delete_user_by_id(db_session, 99999, test_admin)

    def test_delete_self_forbidden(self, db_session, test_admin):
        """测试不能删除自己"""
        with pytest.raises(ValueError, match="不能删除自己"):
            delete_user_by_id(db_session, test_admin.id, test_admin)

    def test_delete_admin_forbidden(self, db_session, test_admin):
        """测试不能删除超级管理员"""
        another_admin = db_create_user(db_session, "another_admin", "pass123", "admin")
        with pytest.raises(ValueError, match="不能删除超级管理员"):
            delete_user_by_id(db_session, another_admin.id, test_admin)


class TestChangePasswordService:
    """修改密码 - 服务层"""

    def test_change_password_success(self, db_session, test_user):
        """测试成功修改密码"""
        result = change_user_password(
            db_session,
            test_user,
            "testpass123",
            "newpass456"
        )

        assert result is True
        assert verify_password("newpass456", test_user.password)

    def test_change_password_with_wrong_old_password(self, db_session, test_user):
        """测试使用错误的原密码修改失败"""
        with pytest.raises(ValueError, match="原密码错误"):
            change_user_password(
                db_session,
                test_user,
                "wrongpass",
                "newpass456"
            )

    def test_change_password_too_long(self, db_session, test_user):
        """测试新密码过长抛出异常"""
        long_password = "a" * 100

        with pytest.raises(ValueError, match="新密码过长"):
            change_user_password(
                db_session,
                test_user,
                "testpass123",
                long_password
            )


# ============================================================
# API 层测试
# ============================================================

class TestUserManagementAPI:
    """用户管理 API 测试（管理员）"""

    def test_list_users_as_admin(self, client, admin_headers):
        """测试管理员获取用户列表"""
        response = client.get("/api/users?page=1&size=10", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "list" in data["data"]
        assert "total" in data["data"]

    def test_list_users_as_user_forbidden(self, client, auth_headers):
        """测试普通用户获取用户列表被拒绝"""
        response = client.get("/api/users?page=1&size=10", headers=auth_headers)
        assert response.status_code == 403

    def test_create_user_as_admin(self, client, admin_headers):
        """测试管理员创建用户"""
        response = client.post("/api/users", json={
            "username": "newadminuser",
            "password": "adminpass123"
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_create_user_as_user_forbidden(self, client, auth_headers):
        """测试普通用户创建用户被拒绝"""
        response = client.post("/api/users", json={
            "username": "normaluser",
            "password": "userpass123"
        }, headers=auth_headers)
        assert response.status_code == 403

    def test_delete_user_as_admin(self, client, admin_headers, db_session):
        """测试管理员删除用户"""
        # 先创建一个临时用户
        from database.models.user import User
        from utils.auth import hash_password
        temp_user = User(username="tempuser", password=hash_password("temppass"), role="user")
        db_session.add(temp_user)
        db_session.commit()

        response = client.delete(f"/api/users/{temp_user.id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_get_user_devices_as_admin(self, client, admin_headers, test_user, test_device, db_session):
        """测试管理员查询用户设备"""
        from database.models.user_device import UserDevice
        binding = UserDevice(user_id=test_user.id, device_id=test_device.id)
        db_session.add(binding)
        db_session.commit()

        response = client.get(f"/api/users/{test_user.id}/devices", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_get_nonexistent_user_devices(self, client, admin_headers):
        """测试查询不存在用户的设备"""
        response = client.get("/api/users/99999/devices", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] in [200, 404]

    def test_list_users_with_pagination(self, client, admin_headers):
        """测试用户列表分页"""
        response = client.get("/api/users?page=1&size=5", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "list" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["list"], list)
        assert len(data["data"]["list"]) <= 5

    def test_list_users_with_username_filter(self, client, admin_headers, test_user):
        """测试用户列表按用户名筛选"""
        response = client.get(f"/api/users?username={test_user.username}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["total"] >= 1

    def test_list_users_with_role_filter(self, client, admin_headers):
        """测试用户列表按角色筛选"""
        response = client.get("/api/users?role=admin", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        for user in data["data"]["list"]:
            assert user["role"] == "admin"

    def test_delete_nonexistent_user(self, client, admin_headers):
        """测试删除不存在的用户"""
        response = client.delete("/api/users/99999", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 404
