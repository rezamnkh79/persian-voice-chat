from __future__ import annotations

import asyncio
import json
import logging
import wave
from pathlib import Path
from typing import Any

from backend.providers.stt_base import STTProvider, STTResult

logger = logging.getLogger("voice")

_model_cache: dict[str, Any] = {}


class VoskSTTProvider(STTProvider):
    id = "vosk"
    title = "Vosk فارسی (آفلاین)"
    description = (
        "تشخیص گفتار سبک و محلی با vosk-model-small-fa. بدون اینترنت. "
        "سبک‌تر از Whisper و مناسب CPU."
    )
    offline = True

    def readiness(self, settings: dict[str, Any]) -> tuple[bool, str]:
        try:
            from vosk import Model  # noqa: F401
        except Exception:
            return False, "بسته vosk نصب نیست (pip install vosk)."

        model_path = Path(settings.get("vosk_model_path", ""))
        if not model_path.is_dir():
            return (
                False,
                "مدل Vosk فارسی پیدا نشد. مسیر models/vosk-model-small-fa-0.42 را تنظیم کنید.",
            )
        # basic sanity
        if not (model_path / "am").exists() and not (model_path / "conf").exists():
            return False, f"ساختار مدل Vosk ناقص است: {model_path}"
        return True, f"آماده · {model_path.name}"

    def _load(self, model_path: str):
        if model_path in _model_cache:
            return _model_cache[model_path]
        from vosk import Model

        model = Model(model_path)
        _model_cache[model_path] = model
        return model

    def _transcribe_sync(self, wav_path: Path, settings: dict[str, Any]) -> STTResult:
        from vosk import KaldiRecognizer, SetLogLevel

        SetLogLevel(-1)
        model = self._load(str(settings.get("vosk_model_path", "")))

        with wave.open(str(wav_path), "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                raise RuntimeError("برای Vosk صوت باید mono PCM 16-bit باشد.")
            rate = wf.getframerate()
            duration = wf.getnframes() / float(rate) if rate else 0.0
            rec = KaldiRecognizer(model, rate)
            rec.SetWords(True)
            parts: list[str] = []
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                if rec.AcceptWaveform(data):
                    payload = json.loads(rec.Result())
                    text = (payload.get("text") or "").strip()
                    if text:
                        parts.append(text)
            final = json.loads(rec.FinalResult())
            text = (final.get("text") or "").strip()
            if text:
                parts.append(text)

        joined = " ".join(parts).strip()
        if not joined:
            raise RuntimeError("گفتار تشخیص داده نشد.")
        return STTResult(
            text=joined,
            provider=self.id,
            offline=True,
            duration=round(duration, 2),
        )

    async def transcribe(self, wav_path: Path, settings: dict[str, Any]) -> STTResult:
        ready, detail = self.readiness(settings)
        if not ready:
            raise RuntimeError(detail)
        return await asyncio.to_thread(self._transcribe_sync, wav_path, settings)
