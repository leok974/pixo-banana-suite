from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Dict, Any
from pathlib import Path

@dataclass
class EditItem:
    image_path: str
    instruction: str

class NanoBanana:
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent.parent / "prompts" / "edit"
        self.prompts_dir = Path(prompts_dir)
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    def load_templates(self) -> Dict[str, str]:
        """Load prompt templates"""
        templates = {}
        
        # Try to load system prompt
        system_path = self.prompts_dir / "system.md"
        if system_path.exists():
            templates["system"] = system_path.read_text(encoding="utf-8")
        else:
            templates["system"] = (
                "You are Nano Banana, a careful pixel-art editor. "
                "Apply sprite-safe changes, keep silhouettes intact, avoid blurring. "
                "Return concise directives; never include unsafe or destructive edits."
            )
        
        # Try to load instruction template
        instruction_path = self.prompts_dir / "instruction.md"
        if instruction_path.exists():
            templates["user"] = instruction_path.read_text(encoding="utf-8")
        else:
            templates["user"] = (
                "Instruction: {{instruction}}\n"
                "Requirements: preserve pixel density, avoid global blur, keep character proportions.\n"
                "Output: list the concrete edits/tool steps."
            )
        
        return templates

    def build_prompt(self, item: EditItem) -> str:
        """Build the full prompt for editing"""
        templates = self.load_templates()
        user_prompt = templates["user"].replace("{{instruction}}", item.instruction)
        
        return f"{templates['system']}\n\n{user_prompt}"

    def run_edit_stub(self, item: EditItem) -> Dict[str, Any]:
        """Stub implementation - returns mock result"""
        prompt = self.build_prompt(item)
        
        # In real implementation, this would:
        # 1. Call Gemini API with the prompt
        # 2. Parse the response for edit instructions
        # 3. Apply edits via ComfyUI or other tools
        # 4. Return paths to edited images
        
        return {
            "image_path": item.image_path,
            "instruction": item.instruction,
            "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
            "result": {
                "note": "Stub edit complete - wire to real Gemini/Comfy pipeline",
                "edited_path": f"assets/outputs/edited_{Path(item.image_path).stem}.png"
            }
        }