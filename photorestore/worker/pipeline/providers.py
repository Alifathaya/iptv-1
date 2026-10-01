"""Lapisan generatif OPSIONAL (default nonaktif, pipeline normal tanpa API).
Interface: GenerativeEnhancer.process(image, prompt).

AIProvider
|-- LocalAIProvider   (inpainting goresan + detail, gratis, tanpa API)
|-- OpenAIProvider    (edit generatif, butuh OPENAI_API_KEY di server)

Jangan hard-code OpenAI ke pipeline: pipeline memanggil get_provider()
dan provider yang memutuskan bisa jalan atau tidak.
"""
import os

import cv2
import numpy as np

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-image-1")
# estimasi kasar USD per gambar (lihat dashboard OpenAI untuk tagihan pasti)
OPENAI_COST_EST = {"gpt-image-1": 0.05, "dall-e-2": 0.02}


class UnavailableError(Exception):
    pass


class AIProvider:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def process(self, image: np.ndarray, prompt: str) -> tuple:
        """Return (gambar, catatan). Prompt dipakai bila provider memahaminya."""
        raise NotImplementedError


class LocalAIProvider(AIProvider):
    """Perbaikan kerusakan lokal: deteksi goresan/noda tipis (blackhat)
    lalu inpaint Telea + polish detail. Bukan difusi — jujur dicatat."""
    name = "local-inpaint"

    def available(self) -> bool:
        return True

    def process(self, image, prompt=""):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT,
                                    cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)))
        _, mask = cv2.threshold(blackhat, 30, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        damaged = float((mask > 0).mean() * 100)
        if damaged > 0.01:
            out = cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)
        else:
            out = image.copy()
        return out, {"damaged_pct": round(damaged, 3), "prompt_used": False}


class OpenAIProvider(AIProvider):
    """Edit generatif OpenAI (area rusak berat / detail hilang).
    Hanya bila OPENAI_API_KEY ada di server. Tak pernah di APK."""
    name = "openai"

    def available(self) -> bool:
        return bool(OPENAI_API_KEY)

    def process(self, image, prompt="restore old photo, keep identity, natural"):
        import httpx

        ok, buf = cv2.imencode(".png", image)
        if not ok:
            raise ValueError("encode gagal")
        files = {"image": ("input.png", bytes(buf), "image/png")}
        data = {"model": OPENAI_MODEL, "prompt": prompt}
        try:
            r = httpx.post("https://api.openai.com/v1/images/edits", files=files, data=data,
                           headers={"Authorization": "Bearer " + OPENAI_API_KEY}, timeout=600)
        except Exception as e:
            raise UnavailableError(f"OpenAI tidak terjangkau: {e}")
        if r.status_code == 401:
            raise UnavailableError("OPENAI_API_KEY salah")
        if r.status_code != 200:
            raise UnavailableError(f"OpenAI {r.status_code}: {r.text[:300]}")
        try:
            b64 = r.json()["data"][0]["b64_json"]
        except (KeyError, IndexError):
            raise UnavailableError("respons OpenAI tak terduga (minta b64_json)")
        raw = __import__("base64").b64decode(b64)
        out = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if out is None:
            raise UnavailableError("decode hasil OpenAI gagal")
        cost = OPENAI_COST_EST.get(OPENAI_MODEL, 0.05)
        return out, {"model": OPENAI_MODEL, "prompt_used": True, "api_cost_est": cost}


def get_provider(prefer: str = "auto") -> AIProvider:
    """auto: OpenAI bila ada key, kalau tidak lokal. 'local' paksa lokal."""
    if prefer == "local":
        return LocalAIProvider()
    op = OpenAIProvider()
    if op.available():
        return op
    return LocalAIProvider()
