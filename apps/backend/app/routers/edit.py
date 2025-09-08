from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict
from app.services.nano_banana import apply_edit

router = APIRouter()

def _px(s: str) -> str:
    return s.replace("\\", "/")

class EditItemModel(BaseModel):
    image_path: str
    instruction: str

class EditRequest(BaseModel):
    items: List[EditItemModel]

@router.post("/edit")
def edit(req: EditRequest):
    """Process edit requests using Nano Banana via google-genai"""
    results = []
    for item in req.items:
        normalized_path = item.image_path.replace("\\", "/")
        res = apply_edit(image_path=normalized_path, prompt=item.instruction)
        if isinstance(res, dict) and res.get("edited_path"):
            res["edited_path"] = _px(res["edited_path"])
        results.append(res)
    return {"items": results}