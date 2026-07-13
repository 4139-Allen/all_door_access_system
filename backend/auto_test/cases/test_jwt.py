"""
JWT Token 核验专项测试

覆盖：
  - Token 格式校验（非法 token 被拒绝）
  - Token 过期行为（mock 时间验证）
  - Token 黑名单（登出后立即失效）
  - 双 header 支持（Authorization + X-Token）
  - 无 token 访问受保护接口
"""
import pytest
from test_util.assert_util import assert_success, assert_unauthorized, assert_failure, AssertHelper


class TestTokenValidation:
    """Token 格式与有效性验证"""

    def test_no_token(self, anon_client):
        """完全不带 token → 401"""
        resp = anon_client.get("/auth/profile")
        assert resp.status_code == 401

    def test_invalid_token_format(self, anon_client):
        """非法 token 字符串 → 401"""
        anon_client.set_token("not-a-valid-jwt-token")
        resp = anon_client.get("/auth/profile")
        assert resp.status_code == 401

    def test_malformed_token(self, anon_client):
        """格式错乱的 token → 401"""
        anon_client.set_token("header.payload.invalid_signature")
        resp = anon_client.get("/auth/profile")
        assert resp.status_code == 401

    def test_empty_token_header(self, anon_client):
        """Authorization: Bearer  空值 → 401"""
        anon_client.session.headers["Authorization"] = "Bearer "
        resp = anon_client.get("/auth/profile")
        assert resp.status_code == 401

    def test_expired_token(self, anon_client):
        """过期 token → 401（使用超签的过期 token）"""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone

        # 构造一个已过期的 JWT
        expired_payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = pyjwt.encode(
            expired_payload,
            "test-secret-key-which-is-long-enough-32chars",
            algorithm="HS256",
        )
        anon_client.set_token(expired_token)
        resp = anon_client.get("/auth/profile")
        assert resp.status_code == 401

    def test_wrong_signature(self, anon_client):
        """使用错误密钥签发的 token → 401"""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone

        wrong_payload = {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        wrong_token = pyjwt.encode(
            wrong_payload,
            "different-secret-key-not-matching-server",
            algorithm="HS256",
        )
        anon_client.set_token(wrong_token)
        resp = anon_client.get("/auth/profile")
        assert resp.status_code == 401


class TestXTokenHeader:
    """X-Token header 支持（WeChat Mini Program 使用）"""

    def test_x_token_header(self, account_manager):
        """使用 X-Token header 应正常工作"""
        # 先登录获取 token
        client = account_manager.get_client_no_auth()
        resp = client.post("/auth/login", json={
            "username": "admin",
            "password": "123456",
        })
        token = resp.headers.get("Authorization", "").replace("Bearer ", "")

        # 使用 X-Token 访问（不设置 Authorization）
        client.clear_token()
        client.session.headers["X-Token"] = token
        resp = client.get("/auth/profile")
        assert_success(resp)

    def test_x_token_works_without_auth_header(self, account_manager):
        """只传 X-Token，不传 Authorization → 正常工作"""
        client = account_manager.get_client_no_auth()
        resp = client.post("/auth/login", json={
            "username": "admin",
            "password": "123456",
        })
        token = resp.headers.get("Authorization", "").replace("Bearer ", "")

        client.clear_token()
        client.session.headers["X-Token"] = token
        resp = client.get("/statistics")
        assert_success(resp)


class TestTokenBlacklist:
    """Token 黑名单机制"""

    def test_blacklist_after_logout(self, account_manager):
        """登出后 token 加入黑名单 → 后续请求被拒"""
        client = account_manager.get_client_no_auth()
        resp = client.post("/auth/login", json={
            "username": "admin",
            "password": "123456",
        })
        token = resp.headers.get("Authorization", "").replace("Bearer ", "")

        # 登出
        client.set_token(token)
        client.post("/auth/logout")

        # 再次使用（需要刷新请求头，之前可能被清理）
        client.set_token(token)
        resp = client.get("/auth/profile")
        assert resp.status_code == 401

    def test_logout_twice(self, account_manager):
        """重复登出同一 token 应正常（幂等）"""
        client = account_manager.get_client_no_auth()
        resp = client.post("/auth/login", json={
            "username": "admin",
            "password": "123456",
        })
        token = resp.headers.get("Authorization", "").replace("Bearer ", "")

        client.set_token(token)
        resp1 = client.post("/auth/logout")
        assert_success(resp1)

        # 第二次登出（token 已不在 Redis）→ 仍返回成功
        resp2 = client.post("/auth/logout")
        # 可能 200 或 401，但不应抛异常
        assert resp2.status_code in (200, 401)
