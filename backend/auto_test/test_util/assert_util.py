"""
通用断言工具

职责：
  1. 统一断言响应格式（code / msg / data）
  2. 业务断言（分页结构、字段存在性、类型检查）
  3. 错误信息清晰，定位问题快

用法：
    from test_util.assert_util import assert_success, assert_failure

    data = assert_success(resp)                      # 断言成功并返回 data
    assert_failure(resp, 400, "用户名或密码错误")    # 断言失败

    # 链式校验
    assert_success(resp) \
        .has_field("token") \
        .has_field("role") \
        .has_field("permissions")
"""
from typing import Optional, List, Dict, Any, Type

import requests


# ==================== 基础断言 ====================


class AssertHelper:
    """断言辅助对象，支持链式调用"""

    def __init__(self, body: dict, response: requests.Response = None):
        self.body = body
        self.response = response

    def code_equals(self, expected: int) -> "AssertHelper":
        """断言响应码"""
        actual = self.body.get("code")
        assert actual == expected, (
            f"❌ 响应码不符: 预期 {expected}, 实际 {actual}\n"
            f"   完整响应: {self.body}"
        )
        return self

    def msg_equals(self, expected: str) -> "AssertHelper":
        """断言消息完全匹配"""
        actual = self.body.get("msg", "")
        assert actual == expected, (
            f"❌ 响应消息不符:\n"
            f"   预期: {expected}\n"
            f"   实际: {actual}"
        )
        return self

    def msg_contains(self, keyword: str) -> "AssertHelper":
        """断言消息包含关键字"""
        actual = self.body.get("msg", "")
        assert keyword in actual, (
            f"❌ 响应消息中未找到关键字 '{keyword}': {actual}"
        )
        return self

    def has_field(self, field: str) -> "AssertHelper":
        """断言 data 中存在字段"""
        data = self.body.get("data", {})
        assert field in data, (
            f"❌ data 中缺少字段 '{field}'\n"
            f"   data 内容: {data}"
        )
        return self

    def field_type(self, field: str, expected_type: Type) -> "AssertHelper":
        """断言 data 中字段的类型"""
        data = self.body.get("data", {})
        actual = data.get(field)
        assert isinstance(actual, expected_type), (
            f"❌ 字段 '{field}' 类型不符: "
            f"预期 {expected_type.__name__}, "
            f"实际 {type(actual).__name__} ({actual})"
        )
        return self

    def field_equals(self, field: str, expected) -> "AssertHelper":
        """断言 data 中字段的值"""
        data = self.body.get("data", {})
        actual = data.get(field)
        assert actual == expected, (
            f"❌ 字段 '{field}' 值不符: 预期 {expected}, 实际 {actual}"
        )
        return self

    def data_is_list(self) -> "AssertHelper":
        """断言 data 是列表"""
        data = self.body.get("data")
        assert isinstance(data, list), (
            f"❌ data 应为列表, 实际为 {type(data).__name__}: {data}"
        )
        return self

    def data_is_dict(self) -> "AssertHelper":
        """断言 data 是字典"""
        data = self.body.get("data")
        assert isinstance(data, dict), (
            f"❌ data 应为字典, 实际为 {type(data).__name__}: {data}"
        )
        return self

    def has_pagination(self) -> "AssertHelper":
        """断言分页结构（list / total / page / size）"""
        data = self.body.get("data", {})
        for field in ["list", "total"]:
            assert field in data, (
                f"❌ 分页数据缺少字段 '{field}': {data}"
            )
        return self

    def list_not_empty(self) -> "AssertHelper":
        """断言 data.list 非空"""
        data = self.body.get("data", {})
        items = data.get("list", data if isinstance(data, list) else [])
        assert len(items) > 0, "❌ 数据列表为空，预期非空"
        return self


# ==================== 快捷函数 ====================


def assert_success(
    response: requests.Response,
    expected_msg: str = None,
) -> AssertHelper:
    """
    断言接口调用成功（code=200）

    参数：
        response:     requests.Response 对象
        expected_msg: 可选，期望的 msg 内容

    返回：
        AssertHelper 对象，支持链式调用
    """
    helper = _parse_response(response)
    helper.code_equals(200)
    if expected_msg is not None:
        helper.msg_equals(expected_msg)
    return helper


def assert_created(
    response: requests.Response,
    expected_msg: str = None,
) -> AssertHelper:
    """
    断言创建成功（code=200 且包含创建成功消息）

    用法：
        resp = admin_client.post("/devices", json={...})
        assert_created(resp)
    """
    helper = _parse_response(response)
    helper.code_equals(200)
    if expected_msg:
        helper.msg_contains(expected_msg)
    return helper


def assert_failure(
    response: requests.Response,
    expected_code: int = 400,
    expected_msg_prefix: str = None,
) -> AssertHelper:
    """
    断言接口调用失败

    参数：
        response:            requests.Response 对象
        expected_code:       预期错误码（400/401/403/404/500 等）
        expected_msg_prefix: 可选，预期错误消息前缀

    返回：
        AssertHelper 对象
    """
    helper = _parse_response(response)
    helper.code_equals(expected_code)
    if expected_msg_prefix:
        helper.msg_contains(expected_msg_prefix)
    return helper


# ==================== HTTP 状态码快捷断言 ====================


def assert_unauthorized(response: requests.Response) -> AssertHelper:
    """断言 401 未认证"""
    return assert_failure(response, 401, "认证")


def assert_forbidden(response: requests.Response) -> AssertHelper:
    """断言 403 无权限"""
    return assert_failure(response, 403, "权限")


def assert_not_found(response: requests.Response) -> AssertHelper:
    """断言 404 资源不存在"""
    return assert_failure(response, 404, "不存在")


def assert_validation_error(
    response: requests.Response, expected_msg: str = None
) -> AssertHelper:
    """断言 422 参数校验失败（FastAPI 自动校验）"""
    assert response.status_code == 422, (
        f"❌ HTTP 状态码不符: 预期 422, 实际 {response.status_code}\n"
        f"   响应内容: {response.text[:500]}"
    )
    return AssertHelper(response.json(), response)


# ==================== 内部辅助 ====================


def _parse_response(response: requests.Response) -> AssertHelper:
    """解析响应并返回 AssertHelper"""
    try:
        body = response.json()
    except ValueError:
        raise AssertionError(
            f"❌ 响应不是合法 JSON (HTTP {response.status_code}):\n"
            f"   {response.text[:300]}"
        )
    return AssertHelper(body, response)
