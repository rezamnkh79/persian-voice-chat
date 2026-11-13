"""
Persian Voice Chat — pluggable offline/online TTS & STT
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.audio_util import convert_to_wav, wav_duration_seconds
from backend.providers import get_stt, get_tts, list_stt_meta, list_tts_meta
from backend.settings_store import DEFAULT_SETTINGS, load_settings, reset_settings, save_settings
from backend.textutil import normalize_persian_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("voice")

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "frontend"

app = FastAPI(title="Persian Voice Chat", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: Literal["female", "male"] | None = None
    provider: str | None = None


class SettingsUpdate(BaseModel):
    tts_provider: str | None = None
    stt_provider: str | None = None
    edge_voice: Literal["female", "male"] | None = None
    piper_model_path: str | None = None
    piper_length_scale: float | None = Field(default=None, ge=0.5, le=2.0)
    vosk_model_path: str | None = None
    mms_model_id: str | None = None
    pocket_model_dir: str | None = None
    pocket_voice: Literal["female", "male", "news"] | None = None
    stt_language: str | None = None


def _active_snapshot(settings: dict[str, Any]) -> dict[str, Any]:
    tts_id = settings.get("tts_provider", "piper_mana")
    stt_id = settings.get("stt_provider", "vosk")
    tts_meta = next((m for m in list_tts_meta(settings) if m["id"] == tts_id), None)
    stt_meta = next((m for m in list_stt_meta(settings) if m["id"] == stt_id), None)
    return {
        "status": "ok",
        "settings": settings,
        "tts": tts_meta,
        "stt": stt_meta,
        "providers": {
            "tts": list_tts_meta(settings),
            "stt": list_stt_meta(settings),
        },
    }


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return _active_snapshot(load_settings())


@app.get("/api/settings")
async def get_settings() -> dict[str, Any]:
    return _active_snapshot(load_settings())


@app.put("/api/settings")
async def put_settings(body: SettingsUpdate) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    preview = {**load_settings(), **payload}
    tts_meta = {m["id"]: m for m in list_tts_meta(preview)}
    stt_meta = {m["id"]: m for m in list_stt_meta(preview)}
    if "tts_provider" in payload:
        chosen = tts_meta.get(payload["tts_provider"])
        if not chosen:
            raise HTTPException(status_code=400, detail="ارائه‌دهنده TTS نامعتبر است.")
        if not chosen["ready"]:
            raise HTTPException(
                status_code=400,
                detail=f"TTS «{chosen['title']}» آماده نیست: {chosen['detail']}",
            )
    if "stt_provider" in payload:
        chosen = stt_meta.get(payload["stt_provider"])
        if not chosen:
            raise HTTPException(status_code=400, detail="ارائه‌دهنده STT نامعتبر است.")
        if not chosen["ready"]:
            raise HTTPException(
                status_code=400,
                detail=f"STT «{chosen['title']}» آماده نیست: {chosen['detail']}",
            )
    settings = save_settings(payload)
    return _active_snapshot(settings)


@app.post("/api/settings/reset")
async def settings_reset() -> dict[str, Any]:
    return _active_snapshot(reset_settings())


@app.post("/api/tts")
async def text_to_speech(body: TTSRequest) -> Response:
    text = normalize_persian_text(body.text)
    if not text:
        raise HTTPException(status_code=400, detail="متن خالی است.")

    settings = load_settings()
    if body.voice:
        settings = {**settings, "edge_voice": body.voice}
    provider_id = body.provider or settings.get("tts_provider") or "piper_mana"

    try:
        provider = get_tts(provider_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="ارائه‌دهنده TTS پیدا نشد.") from exc

    ready, detail = provider.readiness(settings)
    if not ready:
        fallback = get_tts("piper_mana")
        fb_ready, fb_detail = fallback.readiness(settings)
        if fb_ready:
            logger.warning(
                "TTS %s not ready (%s); falling back to piper_mana",
                provider_id,
                detail,
            )
            provider = fallback
            provider_id = fallback.id
        else:
            raise HTTPException(
                status_code=400,
                detail=f"TTS آماده نیست: {detail} / جایگزین Piper هم: {fb_detail}",
            )

    logger.info("TTS provider=%s chars=%d", provider_id, len(text))
    try:
        result = await provider.synthesize(text, settings)
    except Exception as exc:
        logger.exception("TTS failed")
        raise HTTPException(status_code=502, detail=f"خطا در TTS ({provider_id}): {exc}") from exc

    ext = "wav" if "wav" in result.media_type else "mp3"
    return Response(
        content=result.audio,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'inline; filename="speech.{ext}"',
            "X-TTS-Provider": result.provider,
            "X-TTS-Offline": "1" if result.offline else "0",
        },
    )


@app.post("/api/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str | None = Form(default=None),
    provider: str | None = Form(default=None),
) -> dict:
    if not audio.filename and not audio.content_type:
        raise HTTPException(status_code=400, detail="فایل صوتی ارسال نشده است.")

    raw = await audio.read()
    if not raw:
        raise HTTPException(status_code=400, detail="فایل صوتی خالی است.")
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="حجم فایل صوتی بیش از حد مجاز است.")

    settings = load_settings()
    if language:
        settings = {**settings, "stt_language": language}
    provider_id = provider or settings.get("stt_provider") or "vosk"

    try:
        stt = get_stt(provider_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="ارائه‌دهنده STT پیدا نشد.") from exc

    if stt.client_side:
        raise HTTPException(
            status_code=400,
            detail=(
                "ارائه‌دهنده مرورگر روی سرور کار نمی‌کند. "
                "میکروفون را در رابط استفاده کنید یا STT را به Vosk تغییر دهید."
            ),
        )

    name = (audio.filename or "audio.wav").lower()
    suffix = ".wav"
    for ext in (".webm", ".ogg", ".mp3", ".m4a", ".wav"):
        if name.endswith(ext):
            suffix = ext
            break

    logger.info("STT provider=%s size=%d suffix=%s", provider_id, len(raw), suffix)

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        wav_path = tmp_path
        if suffix != ".wav":
            converted = tmp_path + ".wav"
            try:
                convert_to_wav(Path(tmp_path), Path(converted))
            except Exception as conv_err:
                raise HTTPException(
                    status_code=400,
                    detail=f"تبدیل صوت ناموفق بود: {conv_err}",
                ) from conv_err
            Path(tmp_path).unlink(missing_ok=True)
            tmp_path = converted
            wav_path = converted

        duration = wav_duration_seconds(Path(wav_path).read_bytes())
        if duration > 120:
            raise HTTPException(status_code=400, detail="حداکثر مدت صوت ۱۲۰ ثانیه است.")

        try:
            result = await stt.transcribe(Path(wav_path), settings)
        except Exception as exc:
            logger.exception("STT failed")
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        text = normalize_persian_text(result.text)
        if not text:
            raise HTTPException(status_code=422, detail="متن تشخیص‌داده‌شده خالی بود.")

        return {
            "text": text,
            "language": settings.get("stt_language", "fa-IR"),
            "duration": result.duration if result.duration is not None else round(duration, 2),
            "provider": result.provider,
            "offline": result.offline,
        }
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/settings")
async def settings_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "settings.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Ensure defaults exist on disk for first run
if not (ROOT / "data" / "settings.json").exists():
    save_settings(DEFAULT_SETTINGS)
