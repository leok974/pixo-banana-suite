from __future__ import annotations
import os
import time
import requests
from typing import Any, Dict, Optional

class ComfyClient:
    def __init__(self, base_url: Optional[str] = None, timeout: int = 120):
        self.base_url = (base_url or os.getenv("COMFY_BASE") or "http://127.0.0.1:8188").rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout

    def submit(self, workflow: Dict[str, Any]) -> str:
        """Submit workflow to ComfyUI"""
        try:
            r = self.session.post(
                f"{self.base_url}/prompt", 
                json={"prompt": workflow}, 
                timeout=30
            )
            r.raise_for_status()
            data = r.json()
            return data.get("prompt_id") or data.get("id") or ""
        except Exception as e:
            print(f"ComfyUI submit error: {e}")
            return ""

    def poll(self, prompt_id: str, interval: float = 1.0, max_wait: float = 300.0) -> Dict[str, Any]:
        """Poll for workflow completion"""
        start = time.time()
        last_response = None
        
        while time.time() - start < max_wait:
            try:
                r = self.session.get(f"{self.base_url}/history/{prompt_id}", timeout=20)
                if r.status_code == 200:
                    data = r.json()
                    if prompt_id in data:
                        status = data[prompt_id].get("status", {})
                        if status.get("status_str") in ["success", "error"]:
                            return data[prompt_id]
                    last_response = data
            except Exception as e:
                print(f"Poll error: {e}")
            
            time.sleep(interval)
        
        return {"status": "timeout", "last": last_response}

    def run(self, workflow: Dict[str, Any], wait: bool = True) -> Dict[str, Any]:
        """Submit and optionally wait for workflow"""
        prompt_id = self.submit(workflow)
        if not prompt_id:
            return {"error": "Failed to submit workflow"}
        
        if not wait:
            return {"prompt_id": prompt_id}
        
        result = self.poll(prompt_id)
        return {"prompt_id": prompt_id, "result": result}