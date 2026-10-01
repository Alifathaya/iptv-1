"""Tahap generatif: hanya jalan bila ctx['generative'] true (default false).
Pipeline normal tidak butuh API apa pun."""
import numpy as np

from .base import Stage, StageResult
from .providers import UnavailableError, get_provider


class GenerativeEnhance(Stage):
    name = "generative"

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        if not ctx.get("generative", False):
            return StageResult(image, {"skipped": True, "reason": "nonaktif default"})
        prompt = ctx.get("prompt", "restore old photo, keep identity, natural")
        provider = get_provider(ctx.get("provider", "auto"))
        try:
            out, notes = provider.process(image, prompt)
        except UnavailableError as e:
            # provider berbayar gagal -> fallback lokal, jangan crash
            from .providers import LocalAIProvider

            out, local_notes = LocalAIProvider().process(image, prompt)
            notes = {"fallback": str(e)[:200], **local_notes, "provider": "local-inpaint"}
            return StageResult(out, notes)
        notes = {"provider": provider.name, **notes}
        if "api_cost_est" in notes:
            ctx["api_cost"] = ctx.get("api_cost", 0.0) + notes["api_cost_est"]
        return StageResult(out, notes)
