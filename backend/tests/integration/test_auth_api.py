"""
认证 API 集成测试（非登录部分）
测试注册、退出、修改密码、Token 校验等
"""
import pytest


class TestRegisterAPI:
    """注册 API 测试"""

    def test_register_new_user(self, client):
        """测试注册新用户"""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "newpass123"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_register_duplicate_user(self, client, test_user):
        """测试注册重复用户"""
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "password": "anotherpass"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400

    def test_register_with_short_password(self, client):
        """测试注册时密码过短"""
        response = client.post("/api/auth/register", json={
            "username": "shortpassuser",
            "password": "123"  # 太短
        })
        assert response.status_code == 422


class TestLogoutAPI:
    """退出登录 API 测试"""

    def test_logout_success(self, client, auth_headers):
        """测试退出登录成功"""
        token = auth_headers["Authorization"].split(" ")[1]
        response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_access_after_logout(self, client, test_user):
        """测试退出登录后 Token 失效"""
        from utils.auth import create_access_token

        # 创建 token
        token = create_access_token(data={"sub": str(test_user.id)})

        # 退出登录
        client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

        # 使用已退出的 token 访问
        response = client.get("/api/devices", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 401
        data = response.json()
        assert "退出" in data.get("detail", "") or "注销" in data.get("detail", "")


class TestChangePasswordAPI:
    """修改密码 API 测试"""

    def test_change_password_success(self, client, db_session, test_user):
        """测试修改密码成功并验证新密码生效"""
        from utils.auth import hash_password

        # 1. 确保数据库中用户的初始密码是我们预期的
        test_user.password = hash_password("testpass123")
        db_session.commit()

        # 2. 先登录获取旧 token
        login_res = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpass123"
        })
        assert login_res.status_code == 200
        old_token = login_res.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {old_token}"}

        # 3. 发送修改密码请求
        response = client.put("/api/auth/password", json={
            "old_password": "testpass123",
            "new_password": "NewSecurePass456!"
        }, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["msg"] == "密码修改成功"

        # 4. 验证旧密码失效
        old_login_res = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpass123"
        })
        assert old_login_res.json()["code"] == 400  # 密码错误

        # 5. 验证新密码生效
        new_login_res = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "NewSecurePass456!"
        })
        assert new_login_res.status_code == 200
        assert new_login_res.json()["code"] == 200
        assert "token" in new_login_res.json()["data"]

    def test_change_password_wrong_old_password(self, client, auth_headers):
        """测试修改密码时原密码错误"""
        response = client.put("/api/auth/password", json={
            "old_password": "wrongpass",
            "new_password": "newpass456"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400

    def test_change_password_too_short(self, client, auth_headers):
        """测试修改密码时新密码过短"""
        response = client.put("/api/auth/password", json={
            "old_password": "testpass123",
            "new_password": "123"  # 太短
        }, headers=auth_headers)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


class TestTokenValidationAPI:
    """Token 校验 API 测试"""

    def test_access_with_expired_token(self, client, test_user, db_session):
        """测试使用过期的 Token 访问"""
        from utils.auth import create_access_token, logout_token
        from database.redis import redis_client

        # 创建一个正常的 token
        token = create_access_token(data={"sub": str(test_user.id)})

        # 手动从 Redis 中删除该 token，模拟过期
        if redis_client:
            redis_client.delete(f"token:{token}")

        # 使用已"过期"的 token 访问
        response = client.get("/api/devices", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 401
        data = response.json()
        assert "退出登录" in data.get("msg", "") or "无效" in data.get("msg", "")

    def test_access_with_malformed_token(self, client):
        """测试使用格式错误的 Token"""
        response = client.get("/api/devices", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 401
        data = response.json()
        # 注意：HTTPException 返回 detail 字段，而非 msg
        assert "无效" in data.get("detail", "") or "过期" in data.get("detail", "")

    def test_access_without_auth_header(self, client):
        """测试缺少 Authorization 头"""
        response = client.get("/api/devices")
        assert response.status_code == 401

    def test_access_with_invalid_token_format(self, client):
        """测试使用无效格式的 Token"""
        response = client.get("/api/devices", headers={
            "Authorization": "InvalidFormat token123"
        })
        assert response.status_code == 401

    def test_access_with_empty_token(self, client):
        """测试使用空 Token"""
        response = client.get("/api/devices", headers={
            "Authorization": "Bearer "
        })
        assert response.status_code == 401
