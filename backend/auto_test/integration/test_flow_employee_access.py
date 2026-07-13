"""
集成测试：新员工开通门禁权限完整流程

业务场景：
  公司新员工需要开通 2 号门禁的权限

流程步骤：
  1. 管理员创建新员工账号         POST /users
  2. 管理员创建设备              POST /devices
  3. 管理员将员工绑定到门禁设备   POST /devices/{id}/bind
  4. 新员工登录获取 token        POST /auth/login
  5. 新员工查看自己的设备列表     GET /devices（应能看到绑定的设备）
  6. 管理员查该员工的设备         GET /users/{id}/devices（确认绑定）
  7. 管理员解绑员工              DELETE /devices/{id}/unbind
  8. 新员工确认设备已消失         GET /devices（列表应为空）
  9. 管理员清理设备 + 员工账号    DELETE /devices/{id} + /users/{id}
"""
import uuid
import pytest
from test_util.assert_util import (
    assert_success, assert_created,
)


class TestNewEmployeeDoorAccessFlow:
    """完整流程：新人开通门禁 → 验证 → 清理"""

    @pytest.mark.destructive
    def test_full_flow(self, account_manager, admin_client):
        # ─── 1. 管理员创建新员工 ───
        employee_name = f"emp_{uuid.uuid4().hex[:8]}"
        resp = admin_client.post("/users", json={
            "username": employee_name,
            "password": "test123456",
        })
        data = assert_created(resp).body["data"]
        employee_id = data["id"]
        assert data["role"] == "user"
        print(f"\n✅ 创建员工: {employee_name} (ID={employee_id})")

        # ─── 2. 管理员创建设备 ───
        device_name = f"DOOR-{uuid.uuid4().hex[:6].upper()}"
        resp = admin_client.post("/devices", json={
            "name": device_name,
            "location": "集成测试-门禁",
        })
        device_data = assert_success(resp).body["data"]
        device_id = device_data["device_id"]
        print(f"✅ 创建设备: {device_name} (ID={device_id})")

        try:
            # ─── 3. 管理员将员工绑定到设备 ───
            resp = admin_client.post(f"/devices/{device_id}/bind", json={
                "user_id": employee_id,
            })
            assert_success(resp, "绑定成功")
            print(f"✅ 绑定员工 {employee_name} → 设备 {device_name}")

            # ─── 4. 新员工登录 ───
            employee_client = account_manager.get_client_no_auth()
            resp = employee_client.post("/auth/login", json={
                "username": employee_name,
                "password": "test123456",
            })
            assert resp.json().get("code") == 200
            token = resp.headers.get("Authorization", "").replace("Bearer ", "")
            employee_client.set_token(token)
            print(f"✅ 员工登录成功")

            # ─── 5. 员工查看自己的设备列表（应能看到绑定的设备） ───
            resp = employee_client.get("/devices?page=1&size=10")
            my_devices = assert_success(resp).body["data"]["list"]
            device_names = [d["name"] for d in my_devices]
            assert device_name in device_names, \
                f"员工设备列表应包含 {device_name}，实际: {device_names}"
            print(f"✅ 员工确认设备 {device_name} 在权限列表中")

            # ─── 6. 管理员查员工的设备确认绑定 ───
            resp = admin_client.get(f"/users/{employee_id}/devices")
            bound_devices = assert_success(resp).body["data"]
            # 接口返回格式: [device_id1, device_id2, ...]
            assert isinstance(bound_devices, list), f"返回应为列表: {bound_devices}"
            assert device_id in bound_devices, \
                f"管理员查员工设备应包含 {device_id}，实际: {bound_devices}"
            print(f"✅ 管理员确认绑定记录存在 (device_id={device_id})")

            # ─── 7. 管理员解绑 ───
            resp = admin_client.delete(f"/devices/{device_id}/unbind?user_id={employee_id}")
            assert resp.status_code == 204
            print(f"✅ 解绑员工 {employee_name} → 设备 {device_name}")

            # ─── 8. 员工确认设备已消失 ───
            resp = employee_client.get("/devices?page=1&size=10")
            my_devices = assert_success(resp).body["data"]["list"]
            device_names = [d["name"] for d in my_devices]
            assert device_name not in device_names, \
                f"解绑后员工设备列表不应包含 {device_name}"
            print(f"✅ 员工确认设备 {device_name} 已从权限列表移除")

            print(f"\n🎉 完整流程测试通过！")
        finally:
            # ─── 9. 清理 ───
            # 先查是否还有绑定关系，有则解绑（防止删设备时报错）
            bound = admin_client.get(f"/users/{employee_id}/devices")
            if bound.ok and device_id in bound.json().get("data", []):
                admin_client.delete(f"/devices/{device_id}/unbind?user_id={employee_id}")
            # 删设备 + 删员工
            admin_client.delete(f"/devices/{device_id}")
            admin_client.delete(f"/users/{employee_id}")
            print(f"✅ 清理完成: 设备 {device_name} + 员工 {employee_name}")
