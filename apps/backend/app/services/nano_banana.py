from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os, base64, traceback, json

@dataclass
class EditItem:
    image_path: str
    instruction: str = ""

class NanoBanana:
    def __init__(self):
        self.api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        # allow overriding per user; provide sensible defaults
        self.model_id = (os.getenv("GEMINI_MODEL") or "").strip()
        if not self.model_id:
            # fallbacks that support image input reasonably
            # prefer a vision-capable quick model
            self.model_id = "gemini-1.5-flash"

    # --------------------
    # Public entry point
    # --------------------
    def run_edit(self, item: EditItem) -> dict:
        """
        Try multiple Gemini client paths in order.
        1) google.genai  (newer) images.edits
        2) google.generativeai (legacy) GenerativeModel.generate_content with inline image
        3) fallback to stub with a visible watermark
        Returns { ok, used_model: 'gemini'|'stub', reason?, result:{edited_path, instruction_used}, debug? }
        """
        if not self.api_key:
            return self.run_edit_stub(item, reason="no_api_key")

        errors = []

        # Path A — google.genai (newer SDK)
        try:
            out = self._try_google_genai_images_edits(item)
            if out:
                return out
        except Exception as e:
            errors.append({"path": "google.genai.images.edits", "err": repr(e), "tb": traceback.format_exc()})

        # Path B — google.generativeai (legacy SDK)
        try:
            out = self._try_google_generativeai_generate_content(item)
            if out:
                return out
        except Exception as e:
            errors.append({"path": "google.generativeai.generate_content", "err": repr(e), "tb": traceback.format_exc()})

        # If all failed, return stub + attach debug for easy visibility
        stub = self.run_edit_stub(item, reason="all_paths_failed")
        stub["debug"] = errors
        return stub

    # --------------------
    # Path A — google.genai
    # --------------------
    def _try_google_genai_images_edits(self, item: EditItem):
        from google import genai  # type: ignore
        client = genai.Client(api_key=self.api_key)

        src = self._ensure_src(item.image_path)
        img_bytes = src.read_bytes()

        # Some SDK builds accept prompt=; others instruction=; we'll try prompt= first.
        try:
            result = client.images.edits(
                model=self.model_id,
                image=img_bytes,
                prompt=item.instruction or "Apply a visible but tasteful edit while preserving the subject."
            )
        except TypeError:
            # try instruction= if prompt signature mismatched
            result = client.images.edits(
                model=self.model_id,
                image=img_bytes,
                instruction=item.instruction or "Apply a visible but tasteful edit while preserving the subject."
            )

        out_bytes = self._extract_image_bytes_genai(result)
        if not out_bytes:
            return None

        edited_rel = self._write_output(src, out_bytes)
        return {
            "ok": True,
            "used_model": "gemini",
            "result": {"edited_path": edited_rel, "instruction_used": item.instruction},
            "path": "google.genai.images.edits"
        }

    def _extract_image_bytes_genai(self, result) -> bytes | None:
        # Handle a few common shapes:
        if hasattr(result, "data") and result.data:
            part = result.data[0]
            b = getattr(part, "b64_data", None) or getattr(part, "data", None)
            if b:
                return self._to_bytes(b)
        if hasattr(result, "image"):
            b = getattr(result.image, "b64_data", None) or getattr(result.image, "data", None)
            if b:
                return self._to_bytes(b)
        if hasattr(result, "bytes"):
            b = getattr(result, "bytes")
            if b:
                return self._to_bytes(b)
        return None

    # --------------------
    # Path B — google.generativeai
    # --------------------
    def _try_google_generativeai_generate_content(self, item: EditItem):
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=self.api_key)

        src = self._ensure_src(item.image_path)
        img_bytes = src.read_bytes()

        model_name = self.model_id or "gemini-1.5-flash"
        model = genai.GenerativeModel(model_name)

        # Inline image + instruction as parts
        parts = [
            {
                "mime_type": "image/png",
                "data": img_bytes,
            },
            item.instruction or "Apply a visible but tasteful edit while preserving the subject.",
        ]

        resp = model.generate_content(parts)

        # Extract first image from candidates/parts
        out_bytes = self._extract_image_bytes_generativeai(resp)
        if not out_bytes:
            return None

        edited_rel = self._write_output(src, out_bytes)
        return {
            "ok": True,
            "used_model": "gemini",
            "result": {"edited_path": edited_rel, "instruction_used": item.instruction},
            "path": "google.generativeai.generate_content"
        }

    def _extract_image_bytes_generativeai(self, resp) -> bytes | None:
        try:
            cands = getattr(resp, "candidates", None) or []
            for c in cands:
                content = getattr(c, "content", None)
                if not content:
                    continue
                parts = getattr(content, "parts", []) or []
                for p in parts:
                    # expect inline_data with mime_type and data (bytes or b64)
                    inline = getattr(p, "inline_data", None)
                    if inline:
                        data = getattr(inline, "data", None)
                        if data:
                            return self._to_bytes(data)
        except Exception:
            pass
        # Some SDK versions use resp._result or resp.prompt_feedback; dump to help debug
        return None

    # --------------------
    # Helpers
    # --------------------
    def _ensure_src(self, path_str: str) -> Path:
        p = Path(path_str)
        if not p.is_absolute():
            p = Path.cwd() / p
        if not p.exists():
            raise FileNotFoundError(f"Source image not found: {p}")
        return p

    def _to_bytes(self, maybe_b64_or_bytes):
        if isinstance(maybe_b64_or_bytes, bytes):
            return maybe_b64_or_bytes
        try:
            return base64.b64decode(maybe_b64_or_bytes)
        except Exception:
            # if it was already a str of raw bytes-like, give up
            return None

    def _write_output(self, src: Path, out_bytes: bytes) -> str:
        out_dir = Path.cwd() / "assets" / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = out_dir / f"edited_{src.stem}.png"
        dst.write_bytes(out_bytes)
        return str(dst.relative_to(Path.cwd()))

    def run_edit_stub(self, item: EditItem, reason: str = "stub") -> dict:
        """
        Copy the image and add a tiny 'STUB' watermark so you can tell it wasn't Gemini.
        """
        src = self._ensure_src(item.image_path)
        out_dir = Path.cwd() / "assets" / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = out_dir / f"edited_{src.stem}.png"

        im = Image.open(src).convert("RGBA")
        draw = ImageDraw.Draw(im)
        text = "STUB"
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        bbox = draw.textbbox((0, 0), text, font=font)
        pad = 4
        x, y = 6, im.height - (bbox[3] - bbox[1]) - 6
        draw.rectangle((x - pad, y - pad, x + (bbox[2] - bbox[0]) + pad, y + (bbox[3] - bbox[1]) + pad), fill=(0, 0, 0, 128))
        draw.text((x, y), text, fill=(255, 255, 255, 224), font=font)

        im.save(dst)
        rel = str(dst.relative_to(Path.cwd()))
        return {
            "ok": True,
            "used_model": "stub",
            "reason": reason,
            "result": {"edited_path": rel, "instruction_used": item.instruction},
        }
