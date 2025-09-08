# apps/backend/app/routers/pipeline.py
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Optional, Any, Dict
from pathlib import Path
import time
import os
import traceback

from app.services.nano_banana import NanoBanana, EditItem
from app.services.pose_maker import make_local_pose_frames
from app.services.anim_utils import build_spritesheet, build_gif

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

@router.get("/ping")
def ping():
    return {"status": "ok"}

@router.get("/roots")
def roots():
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
            "path": str(p).replace("\\", "/"),
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
    now = int(time.time())
    items = []
    for idx in range(min(limit, 8)):
        job_time = now - (60 * (idx + 1))
        job_id = f"demo-{job_time}"
        files = [
            {"kind": "gif", "path": f"assets/outputs/demo_{idx}/anim.gif", "url": f"/view/demo_{idx}/anim.gif" if resolve_urls else None}
        ]
        if idx % 2 == 0:
            files.append({"kind": "sprite_sheet", "path": f"assets/outputs/demo_{idx}/sheet.png", "url": f"/view/demo_{idx}/sheet.png" if resolve_urls else None})
        items.append({
            "job_id": job_id,
            "source": "outputs",
            "created_at": job_time,
            "updated_at": job_time + 50,
            "files": files
        })
    return items

# ---------- EDIT -> POSE -> ANIMATE PIPELINE ----------

class PoseSpec(BaseModel):
    name: str

class PosesPipelineRequest(BaseModel):
    image_path: str                 # original image to edit
    instruction: Optional[str] = "" # nano banana edit instruction (optional)
    poses: List[PoseSpec]           # list of pose names (idle, attack, spell…)
    fps: Optional[int] = 8
    sheet_cols: Optional[int] = 3
    out_dir: Optional[str] = "assets/outputs"
    basename: Optional[str] = None  # if omitted, we create one from the file name

@router.post("/poses")
def poses_pipeline(req: PosesPipelineRequest):
    try:
        # Normalize/resolve
        src = Path(req.image_path.replace("\\", "/"))
        if not src.is_absolute():
            src = Path.cwd() / src
        if not src.exists():
            raise HTTPException(status_code=400, detail=f"Image not found: {src}")

        out_dir = Path((req.out_dir or "assets/outputs").replace("\\", "/"))
        if not out_dir.is_absolute():
            out_dir = Path.cwd() / out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        base = req.basename or src.stem

        # 1) Edit (safe stub)
        edited_path = str(src)
        if (req.instruction or "").strip():
            nb = NanoBanana()
            item = EditItem(image_path=str(src), instruction=req.instruction.strip())
            result = nb.run_edit_stub(item)
            ep = Path(result["result"]["edited_path"])
            edited_path = str(ep if ep.is_absolute() else (Path.cwd() / ep))

        # 2) Poses
        pose_names = [p.name for p in req.poses]
        frames_abs = make_local_pose_frames(edited_path, pose_names, out_dir, base)

        # 3) Artifacts
        sheet_path = build_spritesheet(frames_abs, out_dir, base, cols=req.sheet_cols or 3)
        gif_path   = build_gif(frames_abs, out_dir, base, fps=req.fps or 8)

        def rel(p: Path) -> str:
            return str(p.relative_to(Path.cwd()))

        rel_frames = [rel(Path(f)) for f in frames_abs]
        rel_sheet  = rel(Path(sheet_path))
        rel_gif    = rel(Path(gif_path))

        def to_url(relpath: str) -> str:
            p = Path(relpath)
            return f"/view/{p.relative_to('assets/outputs')}".replace("\\", "/")

        return {
            "job_id": f"poses-{int(time.time())}-{base}",
            "frames": rel_frames,
            "sprite_sheet": rel_sheet,
            "gif": rel_gif,
            "basename": base,
            "urls": {
                "frames": [to_url(f) for f in rel_frames],
                "sprite_sheet": to_url(rel_sheet),
                "gif": to_url(rel_gif),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        # print full traceback to console, return safe 500 text
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"/pipeline/poses failed: {e}")
