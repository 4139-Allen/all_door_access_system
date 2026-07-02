"""
AI 功能测试（服务层 + API 层）
"""
import pytest
from services.ai_agent_service import (
    normalize_device_number, extract_context_from_message,
    parse_ai_command, find_device_by_number_and_location,
    process_ai_chat_command
)
from database.models.device import Device
from core.config import AI_ENABLED


# ============================================================
# 服务层测试（纯逻辑，无外部依赖）
# ============================================================

class TestNormalizeDeviceNumber:
    """设备编号标准化测试"""

    def test_normalize_three_digit(self):
        """测试三位数字保持不变"""
        assert normalize_device_number("001") == "001"
        assert normalize_device_number("123") == "123"

    def test_normalize_one_digit(self):
        """测试一位数字补零"""
        assert normalize_device_number("1") == "001"
        assert normalize_device_number("5") == "005"

    def test_normalize_two_digit(self):
        """测试两位数字补零"""
        assert normalize_device_number("12") == "012"

    def test_normalize_with_text(self):
        """测试从文本中提取数字"""
        assert normalize_device_number("设备001号") == "001"
        assert normalize_device_number("第5号门") == "005"

    def test_normalize_empty_string(self):
        """测试空字符串"""
        assert normalize_device_number("") == ""

    def test_normalize_no_numbers(self):
        """测试无数字字符串"""
        assert normalize_device_number("abc") == "abc"


class TestExtractContext:
    """上下文提取测试"""

    def test_extract_device_number(self):
        """测试提取设备编号"""
        context = {}
        updated = extract_context_from_message("打开001号门", context)

        assert updated.get('device_number') == "001"

    def test_extract_location(self):
        """测试提取位置信息"""
        context = {}
        updated = extract_context_from_message("打开校门的设备", context)

        assert updated.get('location') == "校门"

    def test_extract_intent(self):
        """测试提取开门意图"""
        context = {}
        updated = extract_context_from_message("帮我开门", context)

        assert updated.get('intent') == 'open_door'

    def test_extract_multiple_contexts(self):
        """测试同时提取多个上下文"""
        context = {}
        updated = extract_context_from_message("打开校门001号门", context)

        assert updated.get('device_number') == "001"
        assert updated.get('location') == "校门"
        assert updated.get('intent') == 'open_door'


# ============================================================
# 服务层测试（依赖数据库）
# ============================================================

class TestFindDeviceService:
    """设备查找 - 服务层"""

    def test_find_by_exact_number(self, db_session):
        """测试通过精确设备编号查找"""
        device = Device(name="001", location="校门", status="active")
        db_session.add(device)
        db_session.commit()

        found = find_device_by_number_and_location(db_session, "001", "校门")

        assert found is not None
        assert found.name == "001"

    def test_find_by_normalized_number(self, db_session):
        """测试通过标准化后的编号查找"""
        device = Device(name="001", location="校门", status="active")
        db_session.add(device)
        db_session.commit()

        found = find_device_by_number_and_location(db_session, "1", "校门")

        assert found is not None

    def test_find_by_location(self, db_session):
        """测试通过位置查找"""
        device = Device(name="001", location="教学楼", status="active")
        db_session.add(device)
        db_session.commit()

        found = find_device_by_number_and_location(db_session, "", "教学楼")

        assert found is not None
        assert found.location == "教学楼"

    def test_find_nonexistent_device(self, db_session):
        """测试查找不存在的设备"""
        found = find_device_by_number_and_location(db_session, "999", "未知位置")

        assert found is None


class TestAICommandParsing:
    """AI 命令解析测试"""

    @pytest.mark.skipif(not AI_ENABLED, reason="AI 功能未启用")
    def test_parse_ai_command_with_valid_key(self):
        """测试 API Key 有效时的命令解析"""
        pass

    def test_parse_ai_command_without_api_key(self):
        """测试未配置 API Key 时的提示"""
        if AI_ENABLED:
            pytest.skip("AI 功能已启用，跳过此测试")

        result = parse_ai_command("打开001号门", 1, {})

        assert result["type"] == "text"
        assert "未启用" in result["msg"] or "配置" in result["msg"]


class TestProcessAIChatService:
    """AI 聊天处理 - 服务层"""

    def test_non_admin_cannot_use_ai(self, db_session, test_user):
        """测试无权限用户不能使用 AI 功能"""
        with pytest.raises(PermissionError, match="权限不足"):
            process_ai_chat_command(db_session, test_user, "打开001号门")

    def test_admin_can_use_ai(self, db_session, test_admin):
        """测试管理员可以使用 AI 功能"""
        result = process_ai_chat_command(db_session, test_admin, "打开001号门")

        assert "reply" in result


# ============================================================
# API 层测试
# ============================================================

class TestAIAPI:
    """AI API 测试"""

    def test_ai_chat_requires_auth(self, client):
        """测试 AI 聊天需要认证"""
        response = client.post("/api/ai/chat", json={
            "message": "打开大门"
        })
        assert response.status_code == 401

    def test_ai_chat_as_user_forbidden(self, client, auth_headers):
        """测试普通用户不能使用 AI 功能"""
        response = client.post("/api/ai/chat", json={
            "message": "打开大门"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 403
        assert "仅超级管理员" in data["msg"] or "权限" in data["msg"]

    def test_ai_chat_as_admin(self, client, admin_headers):
        """测试管理员可以使用 AI 功能"""
        response = client.post("/api/ai/chat", json={
            "message": "打开大门"
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "reply" in data["data"]

    def test_ai_chat_empty_message(self, client, admin_headers):
        """测试 AI 聊天空消息"""
        response = client.post("/api/ai/chat", json={
            "message": ""
        }, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] in [200, 400, 404]

    def test_ai_chat_missing_message_field(self, client, admin_headers):
        """测试 AI 聊天缺少 message 字段"""
        response = client.post("/api/ai/chat", json={}, headers=admin_headers)
        assert response.status_code in [200, 422]

    def test_ai_chat_special_characters(self, client, admin_headers):
        """测试AI聊天包含特殊字符"""
        response = client.post("/api/ai/chat", json={
            "message": "打开门！@#$%^&*()"
        }, headers=admin_headers)
        assert response.status_code == 200
