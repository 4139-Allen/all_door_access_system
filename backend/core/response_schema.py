"""
统一响应返回
"""
from pydantic import BaseModel
from typing import Any, Optional


class ApiResponse(BaseModel):
    code: int
    msg: str
    data: Optional[Any] = None


def success(data=None, msg="操作成功") -> dict:
    return {
        "code": 200,
        "msg": msg,
        "data": data
    }


def error(msg="操作失败", code=400) -> dict:
    return {
        "code": code,
        "msg": msg,
        "data": None
    }
