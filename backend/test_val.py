from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime

class TestQuery(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("开始时间不能晚于结束时间")
        return self

try:
    TestQuery(start_time=datetime(2026, 7, 25), end_time=datetime(2026, 7, 24))
except Exception as e:
    print("type:", type(e).__name__)
    print("errors:", e.errors())
