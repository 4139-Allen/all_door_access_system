from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.db import get_db
from utils.auth import get_current_user_obj, require_permission
from database.models.user import User
from services.ai_agent_service import process_ai_chat_command
from utils.api_exception_handler import handle_api_exception
from core.response_schema import success

router = APIRouter(tags=["🤖 AI指令开门"])


class ChatRequest(BaseModel):
    message: str


@router.post("/ai/chat", summary="AI 智能开门", description="通过自然语言指令控制门禁设备")
@handle_api_exception
def ai_chat(
        req: ChatRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_permission("door.open", "device.view"))
):
    """
    AI 智能开门接口

    用户可以用自然语言发送指令，如：
    - "打开大门"
    - "帮我开一下会议室的门"
    - "开启前门"

    AI 会自动识别设备名称并执行开门操作。
    """
    result = process_ai_chat_command(db, current_user, req.message)
    return success(data=result)
