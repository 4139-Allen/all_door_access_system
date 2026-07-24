from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class LogQuery(BaseModel):
    user_id: Optional[int] = Field(None, description="用户ID（仅管理员可用）")
    device_name: Optional[str] = Field(None, max_length=100, description="设备名称模糊搜索")
    status: Optional[str] = Field(None, max_length=50, description="状态筛选（支持前缀匹配，如「失败」匹配「失败：无权限」）")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=100, description="每页数量")

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        if v < 1:
            raise ValueError("每页至少 1 条")
        if v > 100:
            raise ValueError("每页最多 100 条")
        return v


class LogExportQuery(BaseModel):
    """日志导出筛选（不分页，仅筛选条件）"""
    user_id: Optional[int] = Field(None, description="用户ID")
    device_name: Optional[str] = Field(None, max_length=100, description="设备名称模糊搜索")
    status: Optional[str] = Field(None, max_length=50, description="状态筛选")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
