from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Dict
import time
from pathlib import Path
from app.services.anim_utils import create_sprite_sheet, create_gif, normalize_frame_numbers, apply_renames

router = APIRouter()

def _px(s: str) -> str:
  return s.replace("\\", "/")


class AnimateItemModel(BaseModel):
  # Either provide flat frames OR by_pose (preferred)
  frames: Optional[List[str]] = None
  by_pose: Optional[Dict[str, List[str]]] = None
  pose_for_gif: Optional[str] = None
  fps: Optional[int] = 8
  sheet_cols: Optional[int] = 4
  basename: str
  # Sprite sheet options
  fixed_cell: Optional[bool] = None
  cell_w: Optional[int] = None
  cell_h: Optional[int] = None
  normalize_existing: Optional[bool] = True


class AnimateRequest(BaseModel):
  items: List[AnimateItemModel]


@router.post("/animate")
def animate(req: AnimateRequest):
  """Create sprite sheet (row-per-pose) and GIF (from chosen pose or first available)."""
  results = []

  for item in req.items:
    out_dir = Path("assets/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve by_pose map
    if item.by_pose:
      by_pose = {k: [_px(p) for p in v] for k, v in item.by_pose.items()}
    else:
      # fallback: wrap flat frames into a single "all" pose row
      frames = [_px(f) for f in (item.frames or [])]
      by_pose = {"all": frames}

    # Normalize numbering if requested (best effort)
    if item.normalize_existing:
      norm_map, rename_map = normalize_frame_numbers(by_pose, start_index=1, pad=2)
      apply_renames(rename_map)
      by_pose = norm_map

    # Build sprite sheet (row-per-pose)
    sheet_path = (out_dir / f"{item.basename}_sheet.png").as_posix()
    atlas_path = (out_dir / f"{item.basename}_sheet.json").as_posix()
    sheet_path, atlas = create_sprite_sheet(
      by_pose,
      out_sheet_path=sheet_path,
      sheet_cols=item.sheet_cols or 4,
      fixed_cell=bool(item.fixed_cell),
      cell_w=item.cell_w,
      cell_h=item.cell_h,
      out_atlas_path=atlas_path,
      atlas_basename=item.basename,
    )

    # Pick which pose to animate into GIF
    gif_pose = item.pose_for_gif or next((k for k, v in by_pose.items() if v), None)
    gif_frames = by_pose.get(gif_pose, [])
    gif_path = (out_dir / f"{item.basename}.gif").as_posix()
    if gif_frames:
      create_gif(gif_frames, gif_path, fps=item.fps or 8)

    # posix-ify outbound paths
    results.append({
      "basename": item.basename,
      "sprite_sheet": _px(sheet_path),
      "gif": _px(gif_path),
      "gif_pose": gif_pose,
      "frames_used": sum(len(v) for v in by_pose.values()),
      "poses": list(by_pose.keys()),
      "atlas_path": _px(atlas_path),
      "atlas": atlas,
    })

  return {"items": results}
