from __future__ import annotations

import asyncio
import io
import logging
import wave
from pathlib import Path
from typing import Any

from backend.providers.tts_base import TTSProvider, TTSResult

logger = logging.getLogger("voice")

_voice_cache: dict[str, Any] = {}


class PiperManaTTSProvider(TTSProvider):
    id = "piper_mana"
    title = "Mana Persian Piper"
    description = (
        "سبک و سریع روی CPU — مدل fa_IR-mana-medium با بهبود خواندن اضافه. "
        "بهترین گزینه آفلاین برای Production."
    )
    offline = True
    license_note = "مدل Piper / Mana — استفاده محلی"

    def readiness(self, settings: dict[str, Any]) -> tuple[bool, str]:
        try:
            from piper import PiperVoice  # noqa: F401
        except Exception:
            return False, "بسته piper-tts نصب نیست (pip install piper-tts)."

        model = Path(settings.get("piper_model_path", ""))
        json_cfg = Path(str(model) + ".json")
        if not model.is_file() or model.stat().st_size < 1_000_000:
            return (
                False,
                "مدل Mana دانلود نشده. مسیر onnx را در تنظیمات مشخص کنید "
                "(models/Mana-Persian-Piper/fa_IR-mana-medium.onnx).",
            )
        if not json_cfg.is_file():
            return False, f"فایل کانفیگ کنار مدل لازم است: {json_cfg.name}"
        return True, f"آماده · {model.name} ({model.stat().st_size // (1024 * 1024)}MB)"

    def _load(self, model_path: str):
        if model_path in _voice_cache:
            return _voice_cache[model_path]
        from piper import PiperVoice

        voice = PiperVoice.load(model_path)
        _voice_cache[model_path] = voice
        return voice

    def _synth_sync(self, text: str, settings: dict[str, Any]) -> bytes:
        from piper.config import SynthesisConfig

        model_path = str(settings.get("piper_model_path", ""))
        voice = self._load(model_path)
        length_scale = float(settings.get("piper_length_scale", 1.0) or 1.0)
        syn_config = SynthesisConfig(length_scale=length_scale)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            voice.synthesize_wav(text, wf, syn_config=syn_config)
        return buf.getvalue()

    async def synthesize(self, text: str, settings: dict[str, Any]) -> TTSResult:
        ready, detail = self.readiness(settings)
        if not ready:
            raise RuntimeError(detail)
        audio = await asyncio.to_thread(self._synth_sync, text, settings)
        if not audio:
            raise RuntimeError("خروجی صوتی Piper خالی بود.")
        return TTSResult(
            audio=audio,
            media_type="audio/wav",
            provider=self.id,
            offline=True,
        )
