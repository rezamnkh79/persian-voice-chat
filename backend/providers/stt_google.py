from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import speech_recognition as sr

from backend.audio_util import wav_duration_seconds
from backend.providers.stt_base import STTProvider, STTResult

logger = logging.getLogger("voice")


class GoogleSTTProvider(STTProvider):
    id = "google"
    title = "Google Web Speech"
    description = "تشخیص گفتار آنلاین رایگان با زبان fa-IR. نیاز به اینترنت."
    offline = False

    def readiness(self, settings: dict[str, Any]) -> tuple[bool, str]:
        try:
            import speech_recognition  # noqa: F401
        except Exception:
            return False, "بسته SpeechRecognition نصب نیست."
        return True, "آماده (نیاز به اینترنت)"

    def _transcribe_sync(self, wav_path: Path, settings: dict[str, Any]) -> STTResult:
        language = str(settings.get("stt_language") or "fa-IR")
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        duration = wav_duration_seconds(wav_path.read_bytes())

        with sr.AudioFile(str(wav_path)) as source:
            if duration > 0.4:
                recognizer.adjust_for_ambient_noise(source, duration=min(0.3, duration / 3))
            audio_data = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio_data, language=language)
        except sr.UnknownValueError as exc:
            raise RuntimeError(
                "گفتار تشخیص داده نشد. واضح‌تر و با صدای بلندتر صحبت کنید."
            ) from exc
        except sr.RequestError as exc:
            raise RuntimeError(f"سرویس تشخیص گفتار در دسترس نیست: {exc}") from exc

        text = (text or "").strip()
        if not text:
            raise RuntimeError("متن تشخیص‌داده‌شده خالی بود.")
        return STTResult(
            text=text,
            provider=self.id,
            offline=False,
            duration=round(duration, 2),
        )

    async def transcribe(self, wav_path: Path, settings: dict[str, Any]) -> STTResult:
        ready, detail = self.readiness(settings)
        if not ready:
            raise RuntimeError(detail)
        return await asyncio.to_thread(self._transcribe_sync, wav_path, settings)
