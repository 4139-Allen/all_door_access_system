"""
设备测试辅助函数

共享给 test_device.py 和 test_door.py 使用，避免重复代码。
"""
import uuid


def create_device(admin_client) -> int:
    """创建一个测试设备并返回 device_id"""
    resp = admin_client.post("/devices", json={
        "name": f"DEV-{uuid.uuid4().hex[:6].upper()}",
        "location": "自动化测试-设备",
    })
    data = resp.json()
    device_id = data.get("data", {}).get("device_id")
    return device_id


def create_bound_device(admin_client, user_id: int) -> int:
    """创建设备并绑定给指定用户，设备设为 online，返回 device_id"""
    device_id = create_device(admin_client)
    admin_client.post(f"/devices/{device_id}/bind", json={"user_id": user_id})
    admin_client.put(f"/devices/{device_id}", json={"status": "online"})
    return device_id


def cleanup_device(admin_client, device_id: int, user_id: int = None):
    """清理设备（可选先解绑），忽略 404"""
    if user_id:
        admin_client.delete(f"/devices/{device_id}/unbind?user_id={user_id}")
    admin_client.delete(f"/devices/{device_id}")
