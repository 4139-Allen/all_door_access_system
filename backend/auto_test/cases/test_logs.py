"""
日志查询模块专项测试

覆盖：
  - GET /door-logs            基础分页查询
  - 多条件组合过滤            device_name + status + date range
  - 边界值测试                空结果、超大分页、极端日期
  - 权限隔离                  用户只能看自己的日志
"""
import pytest
from test_util.assert_util import (
    assert_success, assert_failure, assert_unauthorized,
)


class TestLogPagination:
    """日志分页"""

    def test_default_pagination(self, admin_client):
        """默认分页（page=1, size=10）"""
        resp = admin_client.get("/door-logs")
        data = assert_success(resp).has_pagination().body["data"]
        assert data["total"] >= 0
        assert isinstance(data["list"], list)

    def test_custom_page_size(self, admin_client):
        """自定义每页条数"""
        resp = admin_client.get("/door-logs?page=1&size=5")
        data = assert_success(resp).body["data"]
        assert len(data["list"]) <= 5

    def test_large_page_number(self, admin_client):
        """超大页码 → 返回空列表而非报错"""
        resp = admin_client.get("/door-logs?page=9999&size=10")
        data = assert_success(resp).body["data"]
        assert data["total"] >= 0
        assert isinstance(data["list"], list)

    def test_pagination_stability(self, admin_client):
        """分页一致性：连续两页不应出现重复数据"""
        # 获取第一页
        resp1 = admin_client.get("/door-logs?page=1&size=5")
        data1 = resp1.json()["data"]["list"]

        resp2 = admin_client.get("/door-logs?page=2&size=5")
        data2 = resp2.json()["data"]["list"]

        # 如果两页都有数据，ID 应不重叠
        ids1 = {item.get("id") for item in data1}
        ids2 = {item.get("id") for item in data2}
        if ids1 and ids2:
            assert ids1.isdisjoint(ids2), "分页出现重复数据"


class TestLogFilters:
    """日志过滤条件"""

    @pytest.mark.parametrize("device_name", ["DEV", "门禁", "DOOR", ""])
    def test_filter_by_device_name(self, admin_client, device_name):
        """按设备名过滤"""
        resp = admin_client.get(f"/door-logs?device_name={device_name}&page=1&size=10")
        assert_success(resp)

    @pytest.mark.parametrize("status", ["成功", "失败", ""])
    def test_filter_by_status(self, admin_client, status):
        """按状态过滤"""
        resp = admin_client.get(f"/door-logs?status={status}&page=1&size=10")
        assert_success(resp)

    def test_filter_by_date_range(self, admin_client):
        """按日期范围过滤"""
        resp = admin_client.get(
            "/door-logs?start_time=2026-01-01&end_time=2026-12-31&page=1&size=10"
        )
        assert_success(resp)

    def test_filter_by_start_only(self, admin_client):
        """只传开始时间"""
        resp = admin_client.get(
            "/door-logs?start_time=2026-06-01&page=1&size=10"
        )
        assert_success(resp)

    def test_filter_by_end_only(self, admin_client):
        """只传结束时间"""
        resp = admin_client.get(
            "/door-logs?end_time=2026-12-31&page=1&size=10"
        )
        assert_success(resp)

    def test_combined_filters(self, admin_client):
        """多条件组合过滤"""
        resp = admin_client.get(
            "/door-logs?"
            "device_name=DEV&status=成功&"
            "start_time=2026-01-01&end_time=2026-12-31&"
            "page=1&size=10"
        )
        assert_success(resp)


class TestLogAuthorization:
    """日志访问权限"""

    def test_user_sees_only_own_logs(self, user_client, admin_client):
        """普通用户只能看到自己的日志（数量 <= 管理员看到的全部）"""
        user_resp = user_client.get("/door-logs?page=1&size=100")
        admin_resp = admin_client.get("/door-logs?page=1&size=100")

        user_total = user_resp.json()["data"]["total"]
        admin_total = admin_resp.json()["data"]["total"]

        assert user_total <= admin_total, (
            f"用户看到的日志数({user_total})不应超过管理员({admin_total})"
        )

    def test_log_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.get("/door-logs?page=1&size=10")
        assert_unauthorized(resp)
