from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict
from app.services.nano_banana import NanoBanana, EditItem

router = APIRouter()

class EditItemModel(BaseModel):
    image_path: str
    instruction: str

class EditRequest(BaseModel):
    items: List[EditItemModel]

@router.post("/edit")
def edit(req: EditRequest):
    """Process edit requests using Nano Banana"""
    nb = NanoBanana()
    results = []
    
    for item in req.items:
        # Normalize Windows paths
        normalized_path = item.image_path.replace("\\", "/")
        edit_item = EditItem(
            image_path=normalized_path,
            instruction=item.instruction
        )
        result = nb.run_edit_stub(edit_item)
        results.append(result)
    
    return {"items": results}