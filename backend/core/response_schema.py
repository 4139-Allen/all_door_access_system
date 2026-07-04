"""
统一响应返回
"""
from pydantic import BaseModel
from typing import Any, Optional


class ApiResponse(BaseModel):
    msg: str
    data: Optional[Any] = None


def success(data=None, msg="操作成功") -> dict:
    return {
        "msg": msg,
        "data": data
    }


def error(msg="操作失败") -> dict:
    return {
        "msg": msg,
        "data": None
    }
