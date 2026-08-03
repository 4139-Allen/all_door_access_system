from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class AlertListQuery(BaseModel):
    """异常事件列表查询参数（非法值由 Pydantic 校验为 422）"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(10, ge=1, le=100, description="每页数量")
    device_name: Optional[str] = Field(None, max_length=100, description="设备名称筛选")
    alert_type: Optional[Literal["lock", "offline", "error"]] = Field(
        None, description="事件类型: lock, offline, error"
    )
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("开始时间不能晚于结束时间")
        return self
