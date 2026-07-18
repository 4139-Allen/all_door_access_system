

BASE_URL = "https://www.doorlink.top"

def test_get_door_logs(admin_client):
    """查看日志"""
    resp = admin_client.get(f"{BASE_URL}/api/door-logs")
    body = resp.json()

    print(f"门禁日志：{body}")
    assert body["code"] == 200
    assert body["msg"] == "获取日志成功"