import os
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image
from google import genai  # type: ignore
from google.genai import types  # type: ignore

DEFAULT_MODEL = os.getenv("NANO_MODEL", "gemini-2.5-flash-image-preview")


def _client() -> genai.Client:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Set GOOGLE_API_KEY")
    return genai.Client(api_key=api_key)  # Developer API client (simple key)


def _pick_mime(path: str) -> str:
    p = path.lower()
    if p.endswith(".png"): return "image/png"
    if p.endswith(".jpg") or p.endswith(".jpeg"): return "image/jpeg"
    if p.endswith(".webp"): return "image/webp"
    return "image/png"


def apply_edit(
    image_path: str,
    prompt: str = "",
    model: Optional[str] = None,
    out_dir: Optional[str] = "assets/outputs",
    watermark_stub: bool = True,  # kept for API parity; SynthID is auto
) -> Dict[str, Any]:
    src = Path(image_path).resolve()
    out = Path(out_dir or "assets/outputs"); out.mkdir(parents=True, exist_ok=True)
    out_png = (out / f"{src.stem}_edit.png").as_posix()

    used_model = model or DEFAULT_MODEL
    reason = ""

    try:
        client = _client()
        img_bytes = src.read_bytes()
        mime = _pick_mime(src.name)

        # Send prompt + image bytes. (Passing image as Part.from_bytes is the documented way.)
        resp = client.models.generate_content(
            model=used_model,
            contents=[
                types.Part.from_text(prompt or "apply subtle improvement"),
                types.Part.from_bytes(data=img_bytes, mime_type=mime),
            ],
        )

        # Find the first inline image in the response and save it
        for cand in getattr(resp, "candidates", []) or []:
            parts = getattr(cand, "content", {}).parts or []
            for part in parts:
                if getattr(part, "inline_data", None) and part.inline_data.mime_type.startswith("image/"):
                    Image.open(BytesIO(part.inline_data.data)).convert("RGBA").save(out_png)
                    return {"used_model": used_model, "edited_path": out_png, "reason": reason}

        raise RuntimeError("Model returned no inline image")

    except Exception as e:
        # Fail soft: copy original so the pipeline keeps going
        try:
            Image.open(src).convert("RGBA").save(out_png)
        except Exception:
            out_png = src.as_posix()
        return {"used_model": "stub", "edited_path": out_png, "reason": f"{type(e).__name__}: {e}"}
