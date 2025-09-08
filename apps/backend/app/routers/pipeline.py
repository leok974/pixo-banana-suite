# apps/backend/app/routers/pipeline.py
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Optional, Any, Dict, Tuple
from pathlib import Path
from PIL import Image
import time
import os
import traceback

from app.services.nano_banana import NanoBanana, EditItem
from app.services.pose_maker import make_local_pose_frames
from app.services.anim_utils import (
    create_sprite_sheet,
    create_gif,
    normalize_frame_numbers,
    apply_renames,
)
from collections import defaultdict
import re

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

@router.get("/ping")
def ping():
    return {"status": "ok"}

@router.get("/selftest")
def selftest():
    return {
        "cwd": os.getcwd(),
        "has_inputs": os.path.isdir("assets/inputs"),
        "has_outputs": os.path.isdir("assets/outputs"),
        "GEMINI_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL"),
    }

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

def _kind_for_path(p: Path) -> str:
    name = p.name.lower()
    if name.endswith(".gif"):
        return "gif"
    if name.endswith(".json") and "sheet" in name:
        return "atlas"
    if "sheet" in name and name.endswith((".png", ".webp")):
        return "sprite_sheet"
    return "image"

def _dir_times(dir_path: Path) -> Tuple[float, float]:
    """(created_at, updated_at) from files; fallback to now."""
    now = time.time()
    mtimes = [f.stat().st_mtime for f in dir_path.rglob("*") if f.is_file()]
    if not mtimes:
        return (now, now)
    return (min(mtimes), max(mtimes))

def _posix(s: str) -> str:
    return s.replace("\\", "/")

@router.get("/status")
def status(
    limit: int = Query(25, ge=1, le=200),
    resolve_urls: bool = Query(False)
):
    """
    Get recent jobs by scanning assets/outputs.
    Each immediate subdirectory under outputs is a 'job'.
    Flat files at outputs/ root are grouped under job_id='outputs-root'.
    """
    base = Path("assets/outputs")
    base.mkdir(parents=True, exist_ok=True)

    jobs: List[Dict[str, Any]] = []

    # 1) Subdirectories as jobs
    for sub in base.iterdir():
        if sub.is_dir():
            created_at, updated_at = _dir_times(sub)
            files = []
            for f in sub.rglob("*"):
                if f.is_file():
                    rel = f.as_posix()
                    url = ("/view/" + os.path.relpath(f, base).replace("\\", "/")) if resolve_urls else None
                    files.append({
                        "kind": _kind_for_path(f),
                        "path": rel,
                        "url": url,
                    })
            jobs.append({
                "job_id": sub.name,
                "source": "outputs",
                "created_at": created_at,
                "updated_at": updated_at,
                "files": files,
            })

    # 2) Root-level files as a single job (optional)
    root_files = [f for f in base.iterdir() if f.is_file()]
    if root_files:
        c, u = _dir_times(base)
        jobs.append({
            "job_id": "outputs-root",
            "source": "outputs",
            "created_at": c,
            "updated_at": u,
            "files": [{
                "kind": _kind_for_path(f),
                "path": f.as_posix(),
                "url": ("/view/" + f.name) if resolve_urls else None,
            } for f in root_files],
        })

    # Newest first
    jobs.sort(key=lambda j: j["updated_at"], reverse=True)
    return jobs[:limit]

# ---------- EDIT -> POSE -> ANIMATE PIPELINE ----------

class PoseSpec(BaseModel):
    name: str
    frames: Optional[int] = None  # per-pose frame count (fan-out)

class PosesPipelineRequest(BaseModel):
    image_path: str                 # original image to edit
    instruction: Optional[str] = "" # nano banana edit instruction (optional)
    poses: List[PoseSpec]           # list of pose names (idle, attack, spell…)
    fps: Optional[int] = 8
    sheet_cols: Optional[int] = 3
    out_dir: Optional[str] = "assets/outputs"
    basename: Optional[str] = None  # if omitted, we create one from the file name
    # NEW: fixed cell-size control
    fixed_cell: Optional[bool] = False
    cell_w: Optional[int] = None
    cell_h: Optional[int] = None
    # NEW: select which pose to animate into GIF (optional)
    pose_for_gif: Optional[str] = None
    # NEW: optionally normalize filenames on disk to 01-based 2-digit padded
    normalize_existing: Optional[bool] = True

@router.post("/poses")
def poses_pipeline(req: PosesPipelineRequest):
    try:
        # Safety belt: default to single idle when none provided
        if not req.poses or len(req.poses) == 0:
            req.poses = [PoseSpec(name="idle")]
        # Validate: frames must be >= 1 when provided
        if any((spec.frames is not None and int(spec.frames) < 1) for spec in req.poses):
            raise HTTPException(status_code=400, detail="Invalid frames; must be >= 1 when provided.")
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

        # 1) Edit (Gemini when available, else stub)
        edit_info = {"used_model": "none", "edited_path": str(src), "reason": None}
        edited_path = str(src)
        if (req.instruction or "").strip():
            nb = NanoBanana()
            item = EditItem(image_path=str(src), instruction=req.instruction.strip())
            result = nb.run_edit(item)  # gemini w/ fallback
            ep = Path(result["result"]["edited_path"])
            edited_path = str(ep if ep.is_absolute() else (Path.cwd() / ep))
            edit_info = {
                "used_model": result.get("used_model", "unknown"),
                "reason": result.get("reason"),
                "edited_path": str(Path(edited_path).relative_to(Path.cwd())),
                "instruction_used": result.get("result", {}).get("instruction_used"),
                "path": result.get("path"),
                "debug": result.get("debug"),  # contains failure details if stub fallback
            }

        # 2) Poses: fan-out strictly 01-based frame names and write stub frames
        pose_frame_map: Dict[str, List[str]] = {}
        all_frames: List[str] = []
        im_src = Image.open(edited_path).convert("RGBA")
        for spec in req.poses:
            n = int(spec.frames) if (spec.frames and spec.frames > 0) else 4
            frames_for_pose: List[str] = []
            for i in range(1, n + 1):
                fname = f"{base}_{spec.name}_{i:02d}.png"
                fpath = (out_dir / fname).as_posix()
                # Write a stub duplicate so downstream sheet/GIF can be created
                im_src.save(fpath)
                frames_for_pose.append(fpath)
                all_frames.append(fpath)
            pose_frame_map[spec.name] = frames_for_pose

        # Optionally normalize existing filenames on disk and update map
        if req.normalize_existing:
            norm_map, rename_map = normalize_frame_numbers(pose_frame_map, start_index=1, pad=2)
            apply_renames(rename_map)
            pose_frame_map = norm_map

        # Build standardized sheet (row-per-pose)
        use_fixed = bool(req.fixed_cell and req.cell_w and req.cell_h)
        frame_size = (int(req.cell_w), int(req.cell_h)) if use_fixed else None
        sheet_path_str = (out_dir / f"{base}_sheet.png").as_posix()
        atlas_path_str = (out_dir / f"{base}_sheet.json").as_posix()
        sheet_path_str, atlas = create_sprite_sheet(
            {k: list(v) for k, v in pose_frame_map.items()},
            out_sheet_path=sheet_path_str,
            sheet_cols=req.sheet_cols or 3,
            fixed_cell=use_fixed,
            cell_w=frame_size[0] if frame_size else None,
            cell_h=frame_size[1] if frame_size else None,
            out_atlas_path=atlas_path_str,
            atlas_basename=base,
        )

        # Choose which pose to animate (request override or first non-empty)
        pose_for_gif = (req.pose_for_gif or next((k for k, v in pose_frame_map.items() if v), None)) or next(iter(pose_frame_map.keys()))
        gif_path_str = (out_dir / f"{base}.gif").as_posix()
        if pose_frame_map.get(pose_for_gif):
            create_gif(pose_frame_map[pose_for_gif], gif_path_str, fps=req.fps or 8)

        def rel(p: Path) -> str:
            return str(p.relative_to(Path.cwd()))

        # Use the (possibly normalized) map to build the flat list of frames
        flat_frames = [p for v in pose_frame_map.values() for p in v]
        rel_frames = [rel(Path(f)) for f in flat_frames]
        rel_sheet = rel(Path(sheet_path_str))
        rel_atlas = rel(Path(atlas_path_str))
        rel_gif = rel(Path(gif_path_str))

        def to_url(relpath: str) -> str:
            p = Path(relpath)
            return f"/view/{p.relative_to('assets/outputs')}".replace("\\", "/")

        # by-pose map with relative paths (for UI to reuse)
        rel_by_pose: Dict[str, List[str]] = {k: [rel(Path(p)) for p in v] for k, v in pose_frame_map.items()}

        # Canonicalize to forward slashes before returning
        rel_frames = [_posix(p) for p in rel_frames]
        rel_by_pose = {k: [_posix(p) for p in v] for k, v in rel_by_pose.items()}
        rel_sheet = _posix(rel_sheet)
        rel_gif = _posix(rel_gif)
        rel_atlas = _posix(rel_atlas)

        payload = {
                "job_id": f"poses-{int(time.time())}-{base}",
                "frames": rel_frames,
                "by_pose": rel_by_pose,
                "sprite_sheet": rel_sheet,
                "gif": rel_gif,
                "atlas_path": rel_atlas,
                "atlas": atlas,
                "gif_pose": pose_for_gif,
                "basename": base,
                "edit_info": edit_info,
                "sheet_options": {
                    "fixed_cell": use_fixed,
                    "cell_w": frame_size[0] if frame_size else None,
                    "cell_h": frame_size[1] if frame_size else None
                },
                "urls": {
                    "frames": [to_url(f) for f in rel_frames],
                    "sprite_sheet": to_url(rel_sheet),
                    "atlas": to_url(rel_atlas),
                    "gif": to_url(rel_gif),
                }
        }
        return payload

    except HTTPException:
        raise
    except Exception as e:
        # print full traceback to console, return safe 500 text
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"/pipeline/poses failed: {e}")
