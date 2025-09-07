from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Literal, Any

router = APIRouter()

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    intent: Optional[Literal["auto", "edit", "animate", "poses"]] = "auto"

@router.post("/agent/chat")
def chat(req: ChatRequest):
    """Process chat messages - stub implementation"""
    last_message = req.messages[-1].content if req.messages else "Hello"
    
    # Stub response
    reply = f"(stub) I understand you want to: {last_message[:50]}..."
    
    # Stub actions based on intent detection
    actions = []
    if "edit" in last_message.lower() or req.intent == "edit":
        actions.append({
            "type": "edit",
            "args": {
                "image_path": "assets/inputs/sprite.png",
                "instruction": last_message
            }
        })
    
    return {
        "reply": reply,
        "actions": actions
    }