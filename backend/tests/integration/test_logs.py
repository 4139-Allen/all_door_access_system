"""
日志查询测试（API 层）
测试门禁日志查询、分页、筛选等功能
"""
import pytest
from datetime import datetime
from database.models.door_log import DoorLog


class TestLogAPI:
    """日志 API 测试"""

    def test_query_logs_requires_auth(self, client):
        """测试查询日志需要认证"""
        response = client.get("/api/door-logs?page=1&size=10")
        assert response.status_code == 401

    def test_query_logs_as_user(self, client, auth_headers):
        """测试普通用户查询自己的日志"""
        response = client.get(
            "/api/door-logs?page=1&size=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_query_logs_as_admin(self, client, admin_headers):
        """测试管理员查询所有日志"""
        response = client.get(
            "/api/door-logs?page=1&size=10",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


class TestLogQueryAdvanced:
    """日志查询高级功能测试"""

    def test_query_logs_with_invalid_page_params(self, client, auth_headers):
        """测试查询日志时使用无效的分页参数"""
        response = client.get("/api/door-logs?page=0&size=0", headers=auth_headers)
        assert response.status_code in [200, 422]

    def test_query_logs_with_large_page_size(self, client, auth_headers):
        """测试查询日志时使用超大分页大小"""
        response = client.get("/api/door-logs?page=1&size=1000", headers=auth_headers)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_query_logs_pagination_consistency(self, client, auth_headers, test_user, test_device, db_session):
        """测试日志分页一致性"""
        # 创建多条日志
        for i in range(15):
            log = DoorLog(
                user_id=test_user.id,
                device_id=test_device.id,
                action="开门",
                status="成功",
                time=datetime.now()
            )
            db_session.add(log)
        db_session.commit()

        # 第一页
        response1 = client.get("/api/door-logs?page=1&size=10", headers=auth_headers)
        data1 = response1.json()

        # 第二页
        response2 = client.get("/api/door-logs?page=2&size=10", headers=auth_headers)
        data2 = response2.json()

        assert data1["code"] == 200
        assert data2["code"] == 200

        # 验证总数一致
        assert data1["data"]["total"] == data2["data"]["total"]
        # 验证第一页和第二页的数据不重叠
        page1_ids = [log["id"] for log in data1["data"]["list"]]
        page2_ids = [log["id"] for log in data2["data"]["list"]]
        assert len(set(page1_ids) & set(page2_ids)) == 0
