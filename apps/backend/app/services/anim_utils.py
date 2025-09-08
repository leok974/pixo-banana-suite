"""
Standards-compliant sprite sheet builder (grouped by pose)
Keeps a compatibility wrapper for build_spritesheet used elsewhere.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageChops, ImageSequence
import imageio.v2 as imageio
import os
import re


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _load_rgba(p: str) -> Image.Image:
    return Image.open(p).convert("RGBA")


def _load_images(paths: List[str]) -> List[Image.Image]:
    """Load a list of image paths as RGBA, skipping unreadable files."""
    imgs: List[Image.Image] = []
    for p in paths:
        if os.path.isfile(p):
            try:
                imgs.append(Image.open(p).convert("RGBA"))
            except Exception:
                # ignore bad files
                pass
    return imgs


def _autotrim(im: Image.Image) -> Image.Image:
    # Trim transparent padding around sprite
    bg = Image.new("RGBA", im.size, (0, 0, 0, 0))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    return im.crop(bbox) if bbox else im


def _pad_to(im: Image.Image, size: Tuple[int, int]) -> Image.Image:
    w, h = size
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = (w - im.width) // 2
    y = (h - im.height) // 2
    canvas.paste(im, (x, y))
    return canvas


def infer_frame_size(frames: List[str], autotrim: bool) -> Tuple[int, int]:
    # Infer a common cell size from the first frame (after optional trim)
    im0 = _load_rgba(frames[0])
    if autotrim:
        im0 = _autotrim(im0)
    return (im0.width, im0.height)


def build_spritesheet_grouped(
    frames_by_pose: Dict[str, List[str]],
    out_dir: Path,
    basename: str,
    frame_size: Optional[Tuple[int, int]] = None,
    padding: int = 0,
    autotrim: bool = True,
) -> Path:
    """
    Build a sheet with one ROW per pose and frames laid LEFT->RIGHT.
    All cells are the same size, RGBA transparent background, no scaling (nearest).
    """
    _ensure_dir(out_dir)

    if not frames_by_pose:
        raise ValueError("No frames provided")

    # Determine consistent cell size
    any_frames = next(iter(frames_by_pose.values()))
    if not any_frames:
        raise ValueError("No frames provided for first pose")
    cell_w, cell_h = frame_size or infer_frame_size(any_frames, autotrim)

    poses = list(frames_by_pose.keys())
    rows = len(poses)
    cols = max((len(frames_by_pose[p]) for p in poses), default=0)

    sheet_w = cols * cell_w + (cols - 1) * padding if cols else cell_w
    sheet_h = rows * cell_h + (rows - 1) * padding if rows else cell_h

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))

    for r, pose in enumerate(poses):
        frames = frames_by_pose[pose]
        for c, f in enumerate(frames):
            im = _load_rgba(f)
            if autotrim:
                im = _autotrim(im)
            # If bigger than cell, reduce by nearest to fit exactly (keeps pixel sharpness)
            if im.width > cell_w or im.height > cell_h:
                im = im.resize((min(im.width, cell_w), min(im.height, cell_h)), Image.NEAREST)
            im = _pad_to(im, (cell_w, cell_h))

            x = c * (cell_w + padding)
            y = r * (cell_h + padding)
            sheet.paste(im, (x, y))

    out_path = out_dir / f"{basename}_sheet.png"
    sheet.save(out_path)
    return out_path


def build_gif(
    frame_paths: List[str],
    out_dir: Path,
    basename: str,
    fps: int = 8,
    autotrim: bool = True,
    frame_size: Optional[Tuple[int, int]] = None,
) -> Path:
    _ensure_dir(out_dir)
    if not frame_paths:
        raise ValueError("No frames provided")
    imgs = [_load_rgba(p) for p in frame_paths]
    if autotrim:
        imgs = [_autotrim(im) for im in imgs]
    if frame_size:
        imgs = [im.resize(frame_size, Image.NEAREST) for im in imgs]
    pal = [im.convert("P", palette=Image.ADAPTIVE) for im in imgs]
    duration = 1.0 / max(1, fps)
    out_path = out_dir / f"{basename}.gif"
    imageio.mimsave(out_path, pal, format="GIF", duration=duration, loop=0)
    return out_path


def create_sprite_sheet(
    frames_by_pose: Dict[str, List[str]],
    out_sheet_path: str,
    sheet_cols: int = 4,
    fixed_cell: bool = False,
    cell_w: Optional[int] = None,
    cell_h: Optional[int] = None,
) -> str:
    """
    Build a row-per-pose sprite sheet. Each row = one pose, left→right frames.
    If fixed_cell=True, every cell is (cell_w x cell_h); otherwise infer max WxH across all frames.
    Note: sheet_cols is currently unused (rows are full-length); kept for API compatibility.
    """
    poses = [k for k, v in frames_by_pose.items() if v]
    if not poses:
        return out_sheet_path

    rows: List[List[Image.Image]] = []
    max_cols = 1
    for pose in poses:
        imgs = _load_images(frames_by_pose[pose])
        if not imgs:
            continue
        rows.append(imgs)
        max_cols = max(max_cols, len(imgs))

    if not rows:
        return out_sheet_path

    # Determine cell size
    if fixed_cell and cell_w and cell_h:
        cw, ch = cell_w, cell_h
    else:
        cw = max(img.width for r in rows for img in r)
        ch = max(img.height for r in rows for img in r)

    # Sheet size
    W = max_cols * cw
    H = len(rows) * ch
    sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    for r, imgs in enumerate(rows):
        for c, img in enumerate(imgs):
            x = c * cw
            y = r * ch
            if fixed_cell:
                ox = x + (cw - img.width) // 2
                oy = y + (ch - img.height) // 2
                sheet.paste(img, (ox, oy), img)
            else:
                sheet.paste(img, (x, y), img)

    Path(out_sheet_path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_sheet_path)
    return out_sheet_path


def create_gif(frames: List[str], out_gif_path: str, fps: int = 8) -> str:
    """Create a looping GIF from a list of frame paths using PIL only."""
    imgs = _load_images(frames)
    if not imgs:
        return out_gif_path
    dur_ms = round(1000 / max(1, fps))
    Path(out_gif_path).parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(
        out_gif_path,
        save_all=True,
        append_images=imgs[1:],
        duration=dur_ms,
        loop=0,
        disposal=2,
        optimize=False,
        transparency=0,
    )
    return out_gif_path


# ---- Compatibility wrapper (flat list -> grouped by inferred pose name) ----
def _group_frames_by_pose(frame_paths: List[str], basename: str) -> Dict[str, List[str]]:
    """
    Try to group frames by pose by parsing filenames of the form
    "{basename}_{pose}_{index}.png". If parsing fails, place all in a single row.
    """
    groups: Dict[str, List[str]] = {}
    for p in frame_paths:
        name = Path(p).stem  # e.g., knightA_attack_01
        pose = None
        if name.startswith(basename + "_"):
            rest = name[len(basename) + 1 :]
            parts = rest.split("_")
            if len(parts) >= 2:
                pose = "_".join(parts[:-1])  # handle underscores in pose names just in case
        if not pose:
            pose = "pose"
        groups.setdefault(pose, []).append(p)
    # keep order stable
    for k in groups:
        groups[k] = sorted(groups[k])
    return groups


def build_spritesheet(
    frame_paths: List[str],
    out_dir: Path,
    basename: str,
    cols: int = 4,
    padding: int = 0,
) -> Path:
    """
    Shim for existing callers: create a grouped sheet by inferring pose groups
    from filenames. Ignores `cols` and uses one row per inferred pose.
    """
    frames_by_pose = _group_frames_by_pose(frame_paths, basename)
    return build_spritesheet_grouped(frames_by_pose, out_dir, basename, padding=padding)


def normalize_frame_numbers(
    by_pose: Dict[str, List[str]],
    start_index: int = 1,
    pad: int = 2,
) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """
    Return a new by_pose with filenames renumbered to a uniform zero-padded scheme.
    Also returns a rename map {old_path -> new_path} to apply on disk if desired.
    We assume names like '<base>_<pose>_<NN>.ext' anywhere in the filename.
    """
    num_re = re.compile(r"^(?P<prefix>.*?_)(?P<num>\d+)(?P<suffix>\.[A-Za-z0-9]+)$")
    rename_map: Dict[str, str] = {}
    new_by_pose: Dict[str, List[str]] = {}

    for pose, paths in by_pose.items():
        new_list: List[str] = []
        idx = start_index
        for p in paths:
            p_norm = p.replace("\\", "/")
            parent = str(Path(p_norm).parent)
            fname = Path(p_norm).name
            m = num_re.match(fname)
            if m:
                new_num = f"{idx:0{pad}d}"
                new_name = f"{m.group('prefix')}{new_num}{m.group('suffix')}"
                new_path = (Path(parent) / new_name).as_posix()
            else:
                stem = Path(fname).stem
                ext = Path(fname).suffix or ".png"
                new_num = f"{idx:0{pad}d}"
                new_name = f"{stem}_{new_num}{ext}"
                new_path = (Path(parent) / new_name).as_posix()

            if new_path != p_norm:
                rename_map[p_norm] = new_path
            new_list.append(new_path)
            idx += 1
        new_by_pose[pose] = new_list

    return new_by_pose, rename_map


def apply_renames(rename_map: Dict[str, str]) -> None:
    """
    Performs os.rename for each mapping if the old path exists.
    Will create parent dirs for new paths if needed.
    """
    for old, new in rename_map.items():
        try:
            old_p = Path(old)
            new_p = Path(new)
            if old_p.exists():
                new_p.parent.mkdir(parents=True, exist_ok=True)
                os.replace(old_p, new_p)
        except Exception:
            # best effort; ignore individual errors
            pass
