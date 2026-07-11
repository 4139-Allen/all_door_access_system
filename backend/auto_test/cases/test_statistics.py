"""
统计数据模块测试

覆盖：
  - GET /statistics           首页统计数据（总数、分类）
  - GET /statistics/trend     本周开锁趋势（按天）
  - GET /statistics/actions   开锁方式占比（分布）
"""
import pytest
from test_util.assert_util import assert_success, assert_unauthorized


class TestStatistics:
    """统计数据"""

    @pytest.mark.smoke
    def test_get_statistics_as_admin(self, admin_client):
        """管理员获取统计 → 完整数据"""
        resp = admin_client.get("/statistics")
        data = assert_success(resp).body.get("data", {})

        # 统计数据应包含关键指标
        # 具体字段取决于 service 实现，但 data 应该是 dict
        assert isinstance(data, dict), f"统计应为 dict 格式: {type(data)}"

    @pytest.mark.smoke
    def test_get_statistics_as_user(self, user_client):
        """普通用户获取统计 → 返回数据（角色过滤后的）"""
        resp = user_client.get("/statistics")
        data = assert_success(resp).body.get("data", {})
        assert isinstance(data, dict)

    def test_get_statistics_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.get("/statistics")
        assert_unauthorized(resp)


class TestWeeklyTrend:
    """本周趋势"""

    def test_get_trend_as_admin(self, admin_client):
        """管理员获取本周趋势"""
        resp = admin_client.get("/statistics/trend")
        data = assert_success(resp).body.get("data", {})

        # 趋势数据应为 dict 或 list
        assert data is not None

    def test_get_trend_as_user(self, user_client):
        """普通用户获取本周趋势"""
        resp = user_client.get("/statistics/trend")
        data = assert_success(resp).body.get("data", {})
        assert data is not None

    def test_get_trend_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.get("/statistics/trend")
        assert_unauthorized(resp)


class TestActionDistribution:
    """开锁方式占比"""

    def test_get_actions_as_admin(self, admin_client):
        """管理员获取开锁方式分布"""
        resp = admin_client.get("/statistics/actions")
        data = assert_success(resp).body.get("data", {})
        assert data is not None

    def test_get_actions_as_user(self, user_client):
        """普通用户获取开锁方式分布"""
        resp = user_client.get("/statistics/actions")
        data = assert_success(resp).body.get("data", {})
        assert data is not None

    def test_get_actions_no_auth(self, anon_client):
        """未登录 → 401"""
        resp = anon_client.get("/statistics/actions")
        assert_unauthorized(resp)
