from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from pathlib import Path
import io, zipfile, time, os

router = APIRouter()

BASE = Path("assets/outputs").resolve()

def _posix(s: str) -> str:
    return s.replace("\\", "/")

def _normalize_input_path(p: Optional[str]) -> Optional[Path]:
    if not p:
        return None
    s = _posix(p)
    # accept /view/* URLs
    if s.startswith("/view/"):
        s = f"assets/outputs/{s[len('/view/'):]}"
    # accept relative project paths or absolute paths
    cand = (Path.cwd() / s).resolve() if not Path(s).is_absolute() else Path(s).resolve()
    # constrain to assets/outputs
    try:
        cand.relative_to(BASE)
    except Exception:
        # if it *is* exactly BASE, allow; else reject
        if cand != BASE:
            return None
    return cand

def _add_if_exists(zf: zipfile.ZipFile, abs_path: Path, arcname: str):
    if abs_path and abs_path.exists() and abs_path.is_file():
        zf.write(abs_path, arcname=arcname)

class ZipRequest(BaseModel):
    # Either provide by_pose OR frames (flat). Paths may be /view/* or filesystem paths under assets/outputs.
    by_pose: Optional[Dict[str, List[str]]] = None
    frames: Optional[List[str]] = None
    sheet_path: Optional[str] = None
    gif_path: Optional[str] = None
    atlas_path: Optional[str] = None
    basename: Optional[str] = "export"
    include_frames: Optional[bool] = True
    include_sheet: Optional[bool] = True
    include_gif: Optional[bool] = True
    include_atlas: Optional[bool] = True
    # Optional extra metadata (e.g., sheet_options)
    meta: Optional[Dict[str, Any]] = None

@router.post("/zip")
def export_zip(req: ZipRequest):
    root_name = (req.basename or "export").strip().replace(" ", "_")
    if not root_name:
        root_name = "export"

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # frames
        if req.include_frames:
            if req.by_pose:
                for pose, lst in req.by_pose.items():
                    for p in (lst or []):
                        abs_p = _normalize_input_path(p)
                        if abs_p:
                            arc = f"{root_name}/frames/{pose}/{abs_p.name}"
                            _add_if_exists(zf, abs_p, arc)
            elif req.frames:
                for p in req.frames:
                    abs_p = _normalize_input_path(p)
                    if abs_p:
                        arc = f"{root_name}/frames/{abs_p.name}"
                        _add_if_exists(zf, abs_p, arc)

        # sheet / gif / atlas (optional)
        if req.include_sheet and req.sheet_path:
            abs_sheet = _normalize_input_path(req.sheet_path)
            if abs_sheet:
                _add_if_exists(zf, abs_sheet, f"{root_name}/{abs_sheet.name}")

        if req.include_gif and req.gif_path:
            abs_gif = _normalize_input_path(req.gif_path)
            if abs_gif:
                _add_if_exists(zf, abs_gif, f"{root_name}/{abs_gif.name}")

        if req.include_atlas and req.atlas_path:
            abs_atlas = _normalize_input_path(req.atlas_path)
            if abs_atlas:
                _add_if_exists(zf, abs_atlas, f"{root_name}/{abs_atlas.name}")

        # lightweight manifest
        manifest = {
            "basename": root_name,
            "created_at": int(time.time()),
            "include_frames": bool(req.include_frames),
            "include_sheet": bool(req.include_sheet),
            "include_gif": bool(req.include_gif),
            "include_atlas": bool(req.include_atlas),
            "poses": list(req.by_pose.keys()) if req.by_pose else None,
            "meta": req.meta or {},
        }
        zf.writestr(f"{root_name}/manifest.json", __import__("json").dumps(manifest, indent=2))

    mem.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{root_name}.zip"',
        "Content-Type": "application/zip",
    }
    return StreamingResponse(mem, headers=headers, media_type="application/zip")
