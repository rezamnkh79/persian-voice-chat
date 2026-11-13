from __future__ import annotations

import io
import logging
from typing import Any

import edge_tts

from backend.providers.tts_base import TTSProvider, TTSResult

logger = logging.getLogger("voice")

EDGE_VOICES = {
    "female": "fa-IR-DilaraNeural",
    "male": "fa-IR-FaridNeural",
}


class EdgeTTSProvider(TTSProvider):
    id = "edge"
    title = "Microsoft Edge TTS"
    description = (
        "کیفیت بالا و صدای طبیعی (دلارا / فرید). نیاز به اینترنت دارد؛ رایگان و بدون API Key."
    )
    offline = False
    license_note = "سرویس آنلاین مایکروسافت Edge"

    def readiness(self, settings: dict[str, Any]) -> tuple[bool, str]:
        try:
            import edge_tts  # noqa: F401
        except Exception:
            return False, "بسته edge-tts نصب نیست."
        return True, "آماده (نیاز به اینترنت)"

    async def synthesize(self, text: str, settings: dict[str, Any]) -> TTSResult:
        voice_key = settings.get("edge_voice", "female")
        voice = EDGE_VOICES.get(str(voice_key), EDGE_VOICES["female"])
        communicate = edge_tts.Communicate(text, voice, rate="+0%")
        audio = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
        data = audio.getvalue()
        if not data:
            raise RuntimeError("خروجی صوتی Edge خالی بود.")
        return TTSResult(
            audio=data,
            media_type="audio/mpeg",
            provider=self.id,
            offline=False,
        )
