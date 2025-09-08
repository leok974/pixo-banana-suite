# apps/backend/app/services/pose_maker.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image


def make_local_pose_frames_map(src_image: str, pose_counts: Dict[str, int], out_dir: Path, basename: str) -> Dict[str, List[str]]:
    """
    Minimal placeholder: duplicate the edited image N times per pose with 01-based numbering.
    Returns a by-pose map of absolute POSIX file paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    src = Path(src_image)
    if not src.is_absolute():
        src = Path.cwd() / src
    im = Image.open(src).convert("RGBA")

    by_pose: Dict[str, List[str]] = {}
    for pose, n in pose_counts.items():
        pose_l = pose.lower()
        lst: List[str] = []
        for i in range(1, int(n) + 1):
            out_path = (out_dir / f"{basename}_{pose_l}_{i:02d}.png").as_posix()
            im.save(out_path)
            lst.append(out_path)
        by_pose[pose] = lst
    return by_pose


def make_local_pose_frames(src_image: str, poses: List[str], out_dir: Path, basename: str) -> List[str]:
    """Backward-compatible wrapper: one frame per pose (01-based)."""
    pose_counts = {p: 1 for p in poses}
    by_pose = make_local_pose_frames_map(src_image, pose_counts, out_dir, basename)
    return [p for lst in by_pose.values() for p in lst]
