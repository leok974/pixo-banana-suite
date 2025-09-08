# apps/backend/app/routers/pipeline.py
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Optional, Any, Dict, Tuple
from pathlib import Path
from PIL import Image
import time
import os
import traceback

from app.services.nano_banana import apply_edit
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

# Tiny helper to ensure forward slashes in all outbound paths
def _px(s: str) -> str:
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
                    rel = _px(f.as_posix())
                    url = ("/view/" + _px(os.path.relpath(f, base))) if resolve_urls else None
                    files.append({
                        "kind": _kind_for_path(f),
                        "path": _px(rel),
                        "url": _px(url) if url else None,
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
                "path": _px(f.as_posix()),
                "url": _px("/view/" + f.name) if resolve_urls else None,
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
    # nano edit options / aliases
    edit_prompt: Optional[str] = None  # alias of instruction
    use_nano: Optional[bool] = True    # run nano banana by default (stub if no key)
    model: Optional[str] = None        # optional model override (unused in current NanoBanana)
    watermark_stub: Optional[bool] = True  # reserved; stub always watermarks currently
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
        src_image = str(src)
        instruction_used = (req.edit_prompt or req.instruction or "").strip()
        try:
            if req.use_nano or instruction_used:
                res = apply_edit(
                    image_path=str(src),
                    prompt=instruction_used,
                    model=req.model,
                    out_dir=str(out_dir),
                    watermark_stub=bool(req.watermark_stub),
                )
                # Extra safety: normalize path directly from the service
                if isinstance(res, dict) and res.get("edited_path"):
                    res["edited_path"] = res["edited_path"].replace("\\", "/")
                edit_info = res
                src_image = edit_info["edited_path"]
        except Exception as e:
            # Fall back to original image while recording the failure in edit_info
            edit_info = {"used_model": "error", "edited_path": str(src), "reason": f"{type(e).__name__}: {e}"}
            src_image = str(src)

        # 2) Poses: fan-out strictly 01-based frame names and write stub frames
        pose_frame_map: Dict[str, List[str]] = {}
        all_frames_abs: List[str] = []
        # Use the normalized edited image path going forward
        im_src = Image.open(src_image).convert("RGBA")
        for spec in req.poses:
            n = int(spec.frames) if (spec.frames and spec.frames > 0) else 4
            frames_for_pose: List[str] = []
            for i in range(1, n + 1):
                fname = f"{base}_{spec.name}_{i:02d}.png"
                fpath = (out_dir / fname).as_posix()
                # Write a stub duplicate so downstream sheet/GIF can be created
                im_src.save(fpath)
                frames_for_pose.append(fpath)
                all_frames_abs.append(fpath)
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

        # Compute relative paths for output artifacts
        sheet_path = rel(Path(sheet_path_str))
        atlas_path = rel(Path(atlas_path_str))
        gif_path = rel(Path(gif_path_str))
        # Build relative by-pose map and flat relative frames
        rel_by_pose: Dict[str, List[str]] = {k: [rel(Path(p)) for p in v] for k, v in pose_frame_map.items()}
        all_frames = [p for p in [fp for v in rel_by_pose.values() for fp in v]]

        def to_url(relpath: str) -> str:
            p = Path(relpath)
            return f"/view/{p.relative_to('assets/outputs')}".replace("\\", "/")

        # posix-ify paths in response
        def _px(s: str) -> str: return s.replace("\\", "/")
        all_frames = [_px(p) for p in all_frames]
        pose_frame_map = {k: [_px(p) for p in v] for k, v in rel_by_pose.items()}
        sheet_path = _px(sheet_path); gif_path = _px(gif_path); atlas_path = _px(atlas_path)
        if isinstance(edit_info, dict) and "edited_path" in edit_info:
            edit_info["edited_path"] = _px(edit_info.get("edited_path", ""))

        payload = {
                "job_id": f"poses-{int(time.time())}-{base}",
                "frames": all_frames,
                "by_pose": pose_frame_map,
                "sprite_sheet": sheet_path,
                "gif": gif_path,
                "atlas_path": atlas_path,
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
                    "frames": [to_url(f) for f in all_frames],
                    "sprite_sheet": to_url(sheet_path),
                    "atlas": to_url(atlas_path),
                    "gif": to_url(gif_path),
                }
        }
        return payload

    except HTTPException:
        raise
    except Exception as e:
        # print full traceback to console, return safe 500 text
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"/pipeline/poses failed: {e}")
