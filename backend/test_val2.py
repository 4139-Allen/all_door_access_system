"""
模拟 FastAPI 校验错误处理流程，看 model_validator 的错误能否被正确捕获
"""
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, model_validator, Field
from typing import Optional
from datetime import datetime

app = FastAPI()

# 注册与项目中相同的错误处理器
from utils.api_exception_handler import register_exception_handlers
register_exception_handlers(app)

class LogQuery(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("开始时间不能晚于结束时间")
        return self

@app.get("/test")
def test(params: LogQuery = Depends()):
    return {"ok": True}

client = TestClient(app)

# 测试 1: 正常请求
r1 = client.get("/test?start_time=2026-07-24&end_time=2026-07-25")
print("正常:", r1.status_code, r1.json())

# 测试 2: 开始 > 结束
r2 = client.get("/test?start_time=2026-07-25&end_time=2026-07-24")
print("开始>结束:", r2.status_code, r2.json())
