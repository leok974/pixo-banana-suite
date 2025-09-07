from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import time
from pathlib import Path

router = APIRouter()

class AnimateItemModel(BaseModel):
    frames: List[str]
    fps: Optional[int] = 8
    sheet_cols: Optional[int] = 4
    basename: str

class AnimateRequest(BaseModel):
    items: List[AnimateItemModel]

@router.post("/animate")
def animate(req: AnimateRequest):
    """Create animations from frames - stub implementation"""
    results = []
    
    for item in req.items:
        # Normalize Windows paths in frames
        frames = [f.replace("\\", "/") for f in item.frames]
        
        result = {
            "sprite_sheet": f"assets/outputs/{item.basename}_sheet.png",
            "gif": f"assets/outputs/{item.basename}.gif",
            "basename": item.basename,
            "frames_used": len(frames)
        }
        results.append(result)
    
    return {"items": results}