"""
统一响应返回

所有 API 响应统一采用以下格式：

    ✅ 成功响应:
        {"code": 200, "msg": "操作成功", "data": { ... }}

    ❌ 错误响应（code 根据异常类型变化）:
        {"code": 400, "msg": "具体错误信息", "data": None}

规范:
    - code  始终存在，200=成功，非200=错误码
    - msg   始终存在，描述业务语义
    - data  始终存在，成功时为业务数据，失败时为 None
    - 翻页列表统一使用 {"total": N, "list": [...]} 格式
"""
from pydantic import BaseModel
from typing import Any, Optional


class ApiResponse(BaseModel):
    """API 统一响应模型（用于 OpenAPI 文档标注）"""
    code: int = 200
    msg: str = "操作成功"
    data: Optional[Any] = None


def success(data=None, msg="操作成功") -> dict:
    """
    统一格式的成功响应。

    参数:
        data: 业务数据，为 None 时前端只关注 msg
        msg:  业务提示语

    返回:
        {"code": 200, "msg": msg, "data": data}
    """
    return {"code": 200, "msg": msg, "data": data}


def error(msg="操作失败", code: int = 400) -> dict:
    """
    统一格式的错误响应。

    参数:
        msg:  具体错误描述
        code: HTTP 状态码 / 业务码

    返回:
        {"code": code, "msg": msg, "data": None}
    """
    return {"code": code, "msg": msg, "data": None}
