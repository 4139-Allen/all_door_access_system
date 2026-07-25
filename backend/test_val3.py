"""验证 Pydantic core ValidationError 能否被 handle_api_exception 正确捕获"""
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel, model_validator, Field
from typing import Optional
from datetime import datetime
from utils.api_exception_handler import handle_api_exception

app = FastAPI()

class LogQuery(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("开始时间不能晚于结束时间")
        return self

@app.get("/test")
@handle_api_exception
def test(params: LogQuery = Depends()):
    return {"ok": True}

client = TestClient(app)

r1 = client.get("/test")
print("无参数:", r1.status_code, r1.json())

r2 = client.get("/test?start_time=2026-07-25&end_time=2026-07-24")
print("开始>结束:", r2.status_code, r2.json())

r3 = client.get("/test?start_time=2026-07-24&end_time=2026-07-25")
print("正常时间:", r3.status_code, r3.json())
