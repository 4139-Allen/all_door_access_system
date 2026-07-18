import json
from pathlib import Path
import pytest
from test_utils.assert_util import assert_success, assert_failure, print_response

BASE_URL = "https://www.doorlink.top"

def load_cases(module, filename):
    """加载data/{module}/{filename}里的测试数据，支持json/yaml"""
    filepath = Path(__file__).parent / "data" / module / filename
    with open(filepath, encoding="utf-8") as f:
        if filename.endswith(".json"):
            data = json.load(f)
        elif filename.endswith((".yaml", ".yml")):
            import yaml
            data = yaml.safe_load(f)

    return data["cases"]



class TestLogin:
    @pytest.mark.smoke
    def test_user_login(self, client):
        """测试登录成功"""
        resp = client.post(
            f"{BASE_URL}/api/auth/login",
            json={"username":"admin","password":"123456"}
        )
        assert resp.json()["code"] == 200
        token = resp.headers.get("Authorization", "").replace("Bearer ", "")
        assert len(token) > 0


#===================参数化，从json/yaml加载数据======================
    #从模块加载数据，只加载一次
    _failure_cases = load_cases("login", "failure_cases.json")


    @pytest.mark.parametrize("case", _failure_cases, ids=lambda c: c["title"])
    def test_login_failure(self, anon_client, case):
        """测试登录失败的多个用例"""
        resp = anon_client.post(
            f"{BASE_URL}/api/auth/login",
            json=case["request"]
        )
        print_response(resp)
        expected = case["expect"]
        data = assert_failure(resp, expected["code"], expected["msg_contains"])




