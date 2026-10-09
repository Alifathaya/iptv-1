"""Foto Jelas Pro — secure OpenAI GPT Image restoration proxy."""
from __future__ import annotations

import base64
import binascii
import logging
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from openai import APIError, AsyncOpenAI, AuthenticationError, PermissionDeniedError, RateLimitError

from .config import ALLOWED_ORIGINS, API_KEY, MAX_UPLOAD_BYTES, OPENAI_API_KEY, OPENAI_IMAGE_MODEL, OPENAI_TIMEOUT_SECONDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Foto Jelas Pro — OpenAI API",
    description="Photo restoration proxy using the OpenAI GPT Image API",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


def verify_api_key(x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None) -> None:
    # Fail closed: do not expose a paid OpenAI-backed endpoint without app auth.
    if not API_KEY:
        raise HTTPException(status_code=503, detail="Backend access key is not configured")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing backend access key")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "foto-jelas-openai",
        "model": OPENAI_IMAGE_MODEL,
        "openai_configured": bool(OPENAI_API_KEY),
    }


@app.get("/v1/info")
def info(_: None = Depends(verify_api_key)) -> dict:
    return {
        "provider": "OpenAI",
        "model": OPENAI_IMAGE_MODEL,
        "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
        "operation": "image restoration/edit",
    }


@app.post("/v1/enhance")
async def enhance_image(
    _: Annotated[None, Depends(verify_api_key)],
    image: UploadFile = File(...),
    deblur: Annotated[int, Form()] = 50,
    sharpness: Annotated[int, Form()] = 60,
    contrast: Annotated[int, Form()] = 25,
) -> Response:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key is not configured on the backend")
    if image.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=415, detail="Use a PNG, JPEG, or WebP image")

    contents = await image.read(MAX_UPLOAD_BYTES + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="Image file is empty")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the upload limit")
    for name, value in (("deblur", deblur), ("sharpness", sharpness), ("contrast", contrast)):
        if not 0 <= value <= 100:
            raise HTTPException(status_code=400, detail=f"{name} must be between 0 and 100")

    prompt = (
        "Restore the supplied photograph, do not create a different image. "
        "Improve visible sharpness, reduce blur and noise, recover natural texture, and balance contrast "
        "while keeping the result photorealistic. Preserve the original person's identity, facial geometry, "
        "age, expression, skin tone, hair, clothing, pose, composition, background, objects, and any text. "
        "Do not beautify, stylize, change identity, add or remove objects, or invent details not supported "
        "by the source. When details are irrecoverable, keep them natural rather than hallucinating features. "
        "Return one restored image. "
        f"Restoration controls (0-100): deblur={deblur}, sharpness={sharpness}, contrast={contrast}."
    )
    try:
        async with AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SECONDS, max_retries=1) as client:
            result = await client.images.edit(
                model=OPENAI_IMAGE_MODEL,
                image=(image.filename or "photo.png", contents, image.content_type),
                prompt=prompt,
                input_fidelity="high",
                quality="high",
                size="auto",
                output_format="png",
            )
    except RateLimitError as exc:
        logger.warning("OpenAI rate limit reached")
        raise HTTPException(status_code=429, detail="OpenAI API rate limit or quota reached") from exc
    except (AuthenticationError, PermissionDeniedError) as exc:
        logger.error("OpenAI authentication or model permission error")
        raise HTTPException(status_code=502, detail="OpenAI rejected the backend API key or model access; check backend configuration") from exc
    except APIError as exc:
        logger.exception("OpenAI image edit request failed")
        raise HTTPException(status_code=502, detail="OpenAI image restoration failed") from exc

    if not result.data or not result.data[0].b64_json:
        raise HTTPException(status_code=502, detail="OpenAI returned no image data")
    try:
        png_bytes = base64.b64decode(result.data[0].b64_json, validate=True)
    except (ValueError, binascii.Error) as exc:
        logger.exception("OpenAI returned invalid base64 image data")
        raise HTTPException(status_code=502, detail="Invalid image data returned by OpenAI") from exc
    return Response(content=png_bytes, media_type="image/png", headers={"Cache-Control": "no-store"})


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
