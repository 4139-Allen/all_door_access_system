from pydantic import BaseModel, Field
from typing import Optional, Literal

# 1. 新增设备
class DeviceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="设备名称")
    location: str = Field(..., min_length=1, max_length=200, description="设备位置")

# 2. 更新设备
class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="设备名称")
    status: Optional[Literal["online", "offline"]] = Field(None, description="设备状态：在线/离线")
    location: Optional[str] = Field(None, min_length=1, max_length=200, description="设备位置")

# 3. 用户 ↔ 设备 绑定（授权）
# 注意：device_id 通过 URL 路径参数传递，此处只需 user_id
class BindUserDevice(BaseModel):
    user_id: int = Field(..., gt=0, description="用户ID")
