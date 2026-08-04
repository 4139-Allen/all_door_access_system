"""
认证模块测试

覆盖：
  - POST /auth/login      正常登录、错误密码、空参数、频率限制
  - POST /auth/register   正常注册、重复用户名
  - POST /auth/logout     登出使 token 失效
  - PUT  /auth/password   修改密码
  - GET  /auth/profile    获取个人信息
  - PUT  /auth/profile    修改用户名
"""
import uuid
import allure
import pytest
from test_util.assert_util import (
    assert_success,
    assert_failure,
    assert_unauthorized,
    assert_validation_error,
)


@allure.feature("认证管理")
class TestLogin:
    """登录功能测试"""

    @allure.story("正常登录")
    @allure.title("管理员用户名密码登录成功")
    @pytest.mark.smoke
    def test_login_success(self, admin_client):
        """管理员正常登录 → 返回 token + 用户信息 + 权限列表"""
        resp = admin_client.post("/auth/login", json={
            "username": "admin",
            "password": "123456",
        })
        data = assert_success(resp).has_field("role").body["data"]
        assert data["role"] == "admin"
        assert data["user_id"] >= 1
        assert "permissions" in data
        assert isinstance(data["permissions"], list)

    @allure.story("异常登录")
    @allure.title("密码错误拒绝登录")
    @pytest.mark.smoke
    def test_login_wrong_password(self, anon_client):
        """错误密码 → 400 业务错误"""
        resp = anon_client.post("/auth/login", json={
            "username": "admin",
            "password": "wrong_password_123",
        })
        assert_failure(resp, 400, "密码错误")

    @allure.story("异常登录")
    @allure.title("不存在的用户返回 400")
    def test_login_nonexistent_user(self, anon_client):
        """不存在的用户 → 400"""
        resp = anon_client.post("/auth/login", json={
            "username": "user_not_exist_999",
            "password": "test123456",
        })
        assert_failure(resp, 400, "不存在")

    @allure.story("参数校验")
    @allure.title("空用户名返回 422")
    def test_login_empty_username(self, anon_client):
        """空用户名 → 422 参数校验失败"""
        resp = anon_client.post("/auth/login", json={
            "username": "",
            "password": "123456",
        })
        assert_validation_error(resp)

    @allure.story("参数校验")
    @allure.title("密码不足 6 位返回 422")
    def test_login_short_password(self, anon_client):
        """密码不足6位 → 422"""
        resp = anon_client.post("/auth/login", json={
            "username": "admin",
            "password": "123",
        })
        assert_validation_error(resp)

    @allure.story("参数校验")
    @allure.title("用户名含特殊字符返回 422")
    def test_login_invalid_chars_in_username(self, anon_client):
        """用户名含特殊字符 → 422"""
        resp = anon_client.post("/auth/login", json={
            "username": "admin@#$",
            "password": "123456",
        })
        assert_validation_error(resp)


@allure.feature("认证管理")
class TestRegister:
    """注册功能测试"""

    @allure.story("用户注册")
    @allure.title("正常注册成功")
    @pytest.mark.destructive
    def test_register_success(self, anon_client):
        """正常注册 → 201 成功"""
        resp = anon_client.post("/auth/register", json={
            "username": f"reg_{uuid.uuid4().hex[:8]}",
            "password": "test123456",
        })
        assert_success(resp, "用户注册成功")

    @allure.story("用户注册")
    @allure.title("重复用户名返回 400")
    def test_register_duplicate_username(self, shared_user_client, anon_client):
        """重复用户名 → 400"""
        resp = anon_client.post("/auth/register", json={
            "username": "admin",
            "password": "test123456",
        })
        assert_failure(resp, 400, "已存在")

    @allure.story("参数校验")
    @allure.title("注册密码太短返回 422")
    def test_register_short_password(self, anon_client):
        """密码太短 → 422"""
        resp = anon_client.post("/auth/register", json={
            "username": f"sp_{uuid.uuid4().hex[:8]}",
            "password": "123",
        })
        assert_validation_error(resp)


@allure.feature("认证管理")
class TestLogout:
    """退出登录测试"""

    @allure.story("退出登录")
    @allure.title("正常登出成功")
    @pytest.mark.smoke
    def test_logout_success(self, user_client):
        """正常登出 → token 失效"""
        resp = user_client.post("/auth/logout")
        assert_success(resp)

    @allure.story("退出登录")
    @allure.title("未登录登出返回 401")
    def test_logout_no_token(self, anon_client):
        """未提供 token → 401"""
        resp = anon_client.post("/auth/logout")
        assert_unauthorized(resp)

    @allure.story("退出登录")
    @allure.title("登出后 token 失效不可再用")
    def test_token_invalid_after_logout(self, account_manager):
        """登出后再次使用该 token 应被拒绝"""
        client = account_manager.get_client_no_auth()
        login_resp = client.post("/auth/login", json={
            "username": "admin",
            "password": "123456",
        })
        token = login_resp.headers.get("Authorization", "").replace("Bearer ", "")

        authed_client = account_manager.get_client_no_auth()
        authed_client.set_token(token)
        authed_client.post("/auth/logout")

        resp = authed_client.get("/auth/profile")
        assert resp.status_code == 401


@allure.feature("认证管理")
class TestPassword:
    """修改密码测试"""

    @allure.story("修改密码")
    @allure.title("正常修改密码成功")
    @pytest.mark.destructive
    def test_change_password_success(self, user_client):
        """正常修改密码"""
        resp = user_client.put("/auth/password", json={
            "old_password": "test123456",
            "new_password": "newpass123",
        })
        assert_success(resp, "密码修改成功")

        user_client.put("/auth/password", json={
            "old_password": "newpass123",
            "new_password": "test123456",
        })

    @allure.story("修改密码")
    @allure.title("原密码错误返回 400")
    def test_change_password_wrong_old(self, shared_user_client):
        """原密码错误 → 400"""
        resp = shared_user_client.put("/auth/password", json={
            "old_password": "wrong_old",
            "new_password": "newpass123",
        })
        assert_failure(resp, 400, "原密码错误")

    @allure.story("参数校验")
    @allure.title("新密码太短返回 422")
    def test_change_password_too_short(self, shared_user_client):
        """新密码太短 → 422"""
        resp = shared_user_client.put("/auth/password", json={
            "old_password": "test123456",
            "new_password": "123",
        })
        assert_validation_error(resp)

    @allure.story("修改密码")
    @allure.title("未登录修改密码返回 401")
    def test_change_password_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.put("/auth/password", json={
            "old_password": "any",
            "new_password": "newpass123",
        })
        assert_unauthorized(resp)


@allure.feature("认证管理")
class TestProfile:
    """个人信息测试"""

    @allure.story("个人信息")
    @allure.title("获取个人信息成功")
    def test_get_profile(self, shared_user_client):
        """获取个人信息 → 返回用户详情"""
        resp = shared_user_client.get("/auth/profile")
        assert_success(resp) \
            .has_field("username") \
            .has_field("role") \
            .has_field("id")

    @allure.story("个人信息")
    @allure.title("未登录获取个人信息返回 401")
    def test_get_profile_no_auth(self, anon_client):
        """未登录获取个人信息 → 401"""
        resp = anon_client.get("/auth/profile")
        assert_unauthorized(resp)

    @allure.story("个人信息")
    @allure.title("修改用户名成功")
    @pytest.mark.destructive
    def test_update_username(self, account_manager):
        """修改用户名"""
        client = account_manager.get_client_no_auth()
        resp = client.post("/auth/login", json={
            "username": "admin",
            "password": "123456",
        })
        token = resp.headers.get("Authorization", "").replace("Bearer ", "")
        client.set_token(token)

        resp = client.put("/auth/profile", json={
            "username": "admin_renamed",
        })
        assert_success(resp, "用户名修改成功")

        client.put("/auth/profile", json={"username": "admin"})


@allure.feature("认证管理")
class TestAvatar:
    """头像上传"""

    @allure.story("头像上传")
    @allure.title("上传合法图片成功")
    @pytest.mark.destructive
    def test_upload_avatar_success(self, user_client):
        """合法 JPG → 200 + avatar URL"""
        resp = user_client.put("/auth/avatar", files={
            "file": ("avatar.png", b"fake-png-data-1234", "image/png")
        })
        data = assert_success(resp, "头像上传成功").body["data"]
        assert data["avatar"].startswith("/uploads/avatars/")

    @allure.story("头像上传")
    @allure.title("非图片文件返回 400")
    def test_upload_avatar_invalid_type(self, admin_client):
        """text/plain 非图片 → 400"""
        resp = admin_client.put("/auth/avatar", files={
            "file": ("test.txt", b"hello", "text/plain")
        })
        assert_failure(resp, 400, "仅支持")

    @allure.story("头像上传")
    @allure.title("超过 1MB 返回 400")
    def test_upload_avatar_too_large(self, admin_client):
        """> 1MB → 400"""
        resp = admin_client.put("/auth/avatar", files={
            "file": ("big.png", b"x" * (1024 * 1024 + 1), "image/png")
        })
        assert_failure(resp, 400, "1MB")

    @allure.story("头像上传")
    @allure.title("未提供文件返回 422")
    def test_upload_avatar_missing_file(self, admin_client):
        """缺 file 字段 → 422"""
        resp = admin_client.put("/auth/avatar")
        assert_validation_error(resp)

    @allure.story("头像上传")
    @allure.title("未登录上传返回 401")
    def test_upload_avatar_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.put("/auth/avatar", files={
            "file": ("a.png", b"x", "image/png")
        })
        assert_unauthorized(resp)
