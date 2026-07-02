"""
门禁控制测试（服务层 + API 层）
"""
import pytest
from datetime import datetime
from services.door_service import open_door_service, _add_door_log
from database.models.user_device import UserDevice
from database.models.door_log import DoorLog
from core.exceptions import NotFoundError


# ============================================================
# 服务层测试
# ============================================================

class TestOpenDoorService:
    """开门服务测试"""

    def test_admin_can_open_any_door(self, db_session, test_admin, test_device):
        """测试管理员可以打开任意门"""
        result = open_door_service(
            db_session,
            test_admin.id,
            test_device.id
        )

        assert result["success"] is True
        assert "开门成功" in result["message"]

        # 验证日志已创建
        log = db_session.query(DoorLog).filter(
            DoorLog.user_id == test_admin.id,
            DoorLog.device_id == test_device.id
        ).first()
        assert log is not None
        assert log.status == "成功"

    def test_user_with_permission_can_open_door(self, db_session, test_user, test_device):
        """测试有权限的普通用户可以开门"""
        # 绑定用户和设备
        binding = UserDevice(user_id=test_user.id, device_id=test_device.id)
        db_session.add(binding)
        db_session.commit()

        result = open_door_service(
            db_session,
            test_user.id,
            test_device.id
        )

        assert result["success"] is True
        assert "开门成功" in result["message"]

    def test_user_without_permission_cannot_open_door(self, db_session, test_user, test_device):
        """测试无权限的普通用户不能开门"""
        with pytest.raises(PermissionError, match="无权限操作：你未绑定该设备，无法开门"):
            open_door_service(
                db_session,
                test_user.id,
                test_device.id
            )
        # 验证失败日志已创建
        log = db_session.query(DoorLog).filter(
            DoorLog.user_id == test_user.id,
            DoorLog.device_id == test_device.id
        ).first()
        assert log is not None
        assert "失败" in log.status
        assert "无权限" in log.status

    def test_open_nonexistent_device(self, db_session, test_user):
        """测试打开不存在的设备"""
        with pytest.raises(NotFoundError, match="设备不存在"):
            open_door_service(
                db_session,
                test_user.id,
                99999  # 不存在的设备
            )


class TestCreateLogService:
    """创建日志测试"""

    def test_create_log_success(self, db_session, test_user, test_device):
        """测试成功创建日志"""
        _add_door_log(db_session, test_user.id, test_device.id, "成功")

        log = db_session.query(DoorLog).order_by(DoorLog.id.desc()).first()
        assert log is not None
        assert log.user_id == test_user.id
        assert log.device_id == test_device.id
        assert log.action == "开门"
        assert log.status == "成功"

    def test_create_log_with_custom_action(self, db_session, test_user, test_device):
        """测试创建自定义操作日志"""
        db_session.add(DoorLog(
            user_id=test_user.id, device_id=test_device.id,
            action="强制开门", status="警告", time=datetime.now()
        ))
        db_session.commit()

        log = db_session.query(DoorLog).order_by(DoorLog.id.desc()).first()
        assert log.action == "强制开门"
        assert log.status == "警告"


# ============================================================
# API 层测试
# ============================================================

class TestDoorAPI:
    """门禁 API 测试"""

    def test_open_door_without_auth(self, client, test_device):
        """测试未认证时开门被拒绝"""
        response = client.post(f"/api/doors/{test_device.id}/open")
        assert response.status_code == 401

    def test_open_door_with_permission(self, client, auth_headers, test_user, test_device, db_session):
        """测试有权限时开门成功"""
        from database.models.user_device import UserDevice

        # 绑定用户和设备
        binding = UserDevice(user_id=test_user.id, device_id=test_device.id)
        db_session.add(binding)
        db_session.commit()

        response = client.post(
            f"/api/doors/{test_device.id}/open",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_open_door_without_permission(self, client, auth_headers, test_device):
        """测试无权限时开门失败"""
        response = client.post(
            f"/api/doors/{test_device.id}/open",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 403

    def test_open_nonexistent_door(self, client, auth_headers):
        """测试打开不存在的门"""
        response = client.post("/api/doors/99999/open", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 404
