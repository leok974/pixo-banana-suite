from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Literal, Optional, Any, Dict
import time
import os
from pathlib import Path

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

@router.get("/ping")
def ping():
    """Fast ping endpoint - no file operations"""
    return {"status": "ok"}

@router.get("/roots")
def roots():
    """Get info about input/output/comfy directories"""
    def check_dir(path: str) -> Dict[str, Any]:
        p = Path(path)
        exists = p.exists() and p.is_dir()
        file_count = 0
        latest_mtime = None
        
        if exists:
            try:
                files = list(p.glob("**/*"))
                file_count = len([f for f in files if f.is_file()])
                if file_count > 0:
                    latest_mtime = max(f.stat().st_mtime for f in files if f.is_file())
            except:
                pass
                
        return {
            "path": path.replace("\\", "/"),
            "exists": exists,
            "file_count": file_count,
            "latest_mtime": latest_mtime
        }
    
    return {
        "inputs": check_dir("assets/inputs"),
        "outputs": check_dir("assets/outputs"),
        "comfy": check_dir(os.getenv("COMFY_OUT", "C:/ComfyUI/outputs"))
    }

@router.get("/status")
def status(
    limit: int = Query(25, ge=1, le=100),
    include: Literal["all", "inputs", "outputs", "comfy"] = Query("all"),
    resolve_urls: bool = Query(False)
):
    """Get recent jobs - returns stub data for now"""
    now = int(time.time())
    items = []
    
    for idx in range(min(limit, 8)):
        job_time = now - (60 * (idx + 1))
        job_id = f"2025-09-07T{12-idx:02d}-34-56Z-demo"
        
        files = []
        if idx % 2 == 0:
            files.append({
                "kind": "sprite_sheet",
                "path": f"assets/outputs/demo_{idx}/sheet.png",
                "url": f"/view/demo_{idx}/sheet.png" if resolve_urls else None
            })
        files.append({
            "kind": "gif",
            "path": f"assets/outputs/demo_{idx}/anim.gif",
            "url": f"/view/demo_{idx}/anim.gif" if resolve_urls else None
        })
        
        items.append({
            "job_id": job_id,
            "source": "outputs",
            "created_at": job_time,
            "updated_at": job_time + 50,
            "files": files
        })
    
    return items

class PoseSpec(BaseModel):
    name: str

class PosesRequest(BaseModel):
    image_path: str
    fps: Optional[int] = 8
    sheet_cols: Optional[int] = 4
    poses: List[PoseSpec]
    out_dir: Optional[str] = "assets/outputs"

@router.post("/poses")
def poses(req: PosesRequest):
    """Generate poses from sprite - stub implementation"""
    # Normalize Windows paths
    image_path = req.image_path.replace("\\", "/")
    base = Path(image_path).stem
    job_id = f"poses-{int(time.time())}-{base}"
    
    # Stub response
    frames = [f"{req.out_dir}/{base}_pose_{i:02d}.png" for i in range(1, 5)]
    
    return {
        "job_id": job_id,
        "frames": frames,
        "sprite_sheet": f"{req.out_dir}/{base}_sheet.png",
        "gif": f"{req.out_dir}/{base}_poses.gif",
        "basename": f"{base}_poses"
    }