"""
统计数据测试（服务层 + API 层）
"""
import pytest
from datetime import datetime, date, timedelta
from services.stat_service import get_statistics, get_today_start
from database.models.device import Device
from database.models.door_log import DoorLog
from database.models.user_device import UserDevice


# ============================================================
# 服务层测试
# ============================================================

class TestGetTodayStart:
    """获取今天开始时间测试"""

    def test_get_today_start_returns_datetime(self):
        """测试返回 datetime 对象"""
        today_start = get_today_start()

        assert isinstance(today_start, datetime)
        assert today_start.hour == 0
        assert today_start.minute == 0
        assert today_start.second == 0

    def test_get_today_start_is_today(self):
        """测试返回的是今天的开始时间"""
        today_start = get_today_start()
        expected = datetime.combine(date.today(), datetime.min.time())

        assert today_start == expected


class TestGetStatisticsService:
    """获取统计数据 - 服务层"""

    def test_admin_statistics(self, db_session, test_admin, test_user, test_device):
        """测试管理员获取全局统计数据"""
        # 创建一些测试数据
        device2 = Device(name="002", location="教学楼", status="online")
        db_session.add(device2)
        db_session.commit()

        # 创建今日日志
        log = DoorLog(
            user_id=test_admin.id,
            device_id=test_device.id,
            action="开门",
            status="成功",
            time=datetime.now()
        )
        db_session.add(log)
        db_session.commit()

        stats = get_statistics(db_session, test_admin)

        assert stats["user_total"] >= 2  # 至少 admin 和 test_user
        assert stats["device_online"] + stats["device_offline"] >= 2  # 至少 test_device 和 device2
        assert stats["today_log"] >= 1

    def test_user_statistics(self, db_session, test_user, test_device):
        """测试普通用户获取个人统计数据"""
        # 绑定设备
        binding = UserDevice(user_id=test_user.id, device_id=test_device.id)
        db_session.add(binding)

        # 创建今日日志
        log = DoorLog(
            user_id=test_user.id,
            device_id=test_device.id,
            action="开门",
            status="成功",
            time=datetime.now()
        )
        db_session.add(log)
        db_session.commit()

        stats = get_statistics(db_session, test_user)

        assert stats["user_total"] == 1  # 普通用户只能看到自己
        assert stats["device_online"] + stats["device_offline"] == 1  # 只看到绑定的设备
        assert stats["today_log"] == 1

    def test_user_statistics_no_bindings(self, db_session, test_user):
        """测试无绑定设备的用户统计数据"""
        stats = get_statistics(db_session, test_user)

        assert stats["user_total"] == 1
        assert stats["device_online"] + stats["device_offline"] == 0
        assert stats["today_log"] == 0

    def test_statistics_with_old_logs(self, db_session, test_user, test_device):
        """测试统计不包含昨天的日志"""
        # 创建昨天的日志
        yesterday = datetime.now() - timedelta(days=1)
        old_log = DoorLog(
            user_id=test_user.id,
            device_id=test_device.id,
            action="开门",
            status="成功",
            time=yesterday
        )
        db_session.add(old_log)

        # 创建今天的日志
        today_log = DoorLog(
            user_id=test_user.id,
            device_id=test_device.id,
            action="开门",
            status="成功",
            time=datetime.now()
        )
        db_session.add(today_log)
        db_session.commit()

        stats = get_statistics(db_session, test_user)

        # 只应该统计今天的日志
        assert stats["today_log"] == 1


# ============================================================
# API 层测试
# ============================================================

class TestStatAPI:
    """统计 API 测试"""

    def test_get_statistics_requires_auth(self, client):
        """测试获取统计数据需要认证"""
        response = client.get("/api/statistics")
        assert response.status_code == 401

    def test_get_statistics_as_user(self, client, auth_headers):
        """测试普通用户获取统计数据"""
        response = client.get("/api/statistics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "user_total" in data["data"]
        assert "device_total" in data["data"]
        assert "today_log" in data["data"]

    def test_get_statistics_as_admin(self, client, admin_headers):
        """测试管理员获取统计数据"""
        response = client.get("/api/statistics", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["user_total"] >= 1
        assert data["data"]["device_total"] >= 0
        assert data["data"]["today_log"] >= 0

    def test_statistics_caching(self, client, auth_headers):
        """测试统计数据缓存机制"""
        # 第一次请求
        response1 = client.get("/api/statistics", headers=auth_headers)
        assert response1.status_code == 200

        # 第二次请求（应该使用缓存）
        response2 = client.get("/api/statistics", headers=auth_headers)
        assert response2.status_code == 200

        # 两次数据应该一致
        assert response1.json()["data"] == response2.json()["data"]
