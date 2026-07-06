import json
import logging
import random
import time

import requests
from django.conf import settings

from tv_channel.services.logo_generation.base import LogoGenerationError, LogoImageBackend
from utils.format_with_jinja import format_with_jinja

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2


class ComfyUiImageBackend(LogoImageBackend):
    """Backend local ComfyUI: rend le workflow Jinja, soumet le prompt,
    poll l'historique puis telecharge l'image produite."""

    name = "comfyui"

    def __init__(self, *, base_url: str | None = None, timeout_seconds: int | None = None):
        self.base_url = (base_url or settings.COMFYUI_URL or "").rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.COMFYUI_TIMEOUT_SECONDS
        self.workflow_template = settings.COMFYUI_WORKFLOW_TEMPLATE
        if not self.base_url:
            raise LogoGenerationError("COMFYUI_URL is not configured.")

    def generate(self, prompt: str) -> bytes:
        workflow = self._render_workflow(prompt)
        prompt_id = self._submit(workflow)
        outputs = self._wait_for_outputs(prompt_id)
        return self._download_first_image(outputs)

    def _render_workflow(self, prompt: str) -> dict:
        rendered = format_with_jinja(
            self.workflow_template,
            {
                "prompt": prompt,
                "negative_prompt": (
                    "photo, photography, watermark, text paragraph, mockup, "
                    "device frame, blurry, low quality"
                ),
                "seed": random.randint(0, 2**32 - 1),
            },
        )
        try:
            return json.loads(rendered)
        except json.JSONDecodeError as exc:
            raise LogoGenerationError(f"Invalid ComfyUI workflow template: {exc}") from exc

    def _submit(self, workflow: dict) -> str:
        response = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow},
            timeout=30,
        )
        if response.status_code != 200:
            raise LogoGenerationError(
                f"ComfyUI rejected the workflow (HTTP {response.status_code}): {response.text[:500]}"
            )
        prompt_id = response.json().get("prompt_id")
        if not prompt_id:
            raise LogoGenerationError("ComfyUI did not return a prompt_id.")
        return prompt_id

    def _wait_for_outputs(self, prompt_id: str) -> dict:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            response = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=30)
            if response.status_code == 200:
                entry = response.json().get(prompt_id)
                if entry:
                    status = entry.get("status", {})
                    if status.get("status_str") == "error":
                        raise LogoGenerationError(f"ComfyUI workflow failed: {status}")
                    outputs = entry.get("outputs")
                    if outputs:
                        return outputs
            time.sleep(POLL_INTERVAL_SECONDS)
        raise LogoGenerationError(f"ComfyUI generation timed out after {self.timeout_seconds}s.")

    def _download_first_image(self, outputs: dict) -> bytes:
        for node_output in outputs.values():
            for image in node_output.get("images", []):
                params = {
                    "filename": image.get("filename"),
                    "subfolder": image.get("subfolder", ""),
                    "type": image.get("type", "output"),
                }
                if not params["filename"]:
                    continue
                response = requests.get(f"{self.base_url}/view", params=params, timeout=60)
                if response.status_code == 200:
                    return response.content
        raise LogoGenerationError("ComfyUI produced no downloadable image.")
