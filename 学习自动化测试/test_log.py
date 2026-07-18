
from test_utils.assert_util import assert_success, assert_failure

BASE_URL = "https://www.doorlink.top"

def test_get_door_logs(admin_client):
    """管理员查看日志"""
    resp = admin_client.get(f"{BASE_URL}/api/door-logs")
    data = assert_success(resp, expected_msg="获取日志成功")
