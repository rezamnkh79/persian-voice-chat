from __future__ import annotations

import asyncio
import io
import logging
import wave
from pathlib import Path
from typing import Any

import numpy as np

from backend.providers.tts_base import TTSProvider, TTSResult

logger = logging.getLogger("voice")

_REQUIRED = (
    "manifest.json",
    "flow_lm_step.onnx",
    "mimi_encoder.onnx",
    "mimi_decoder_step_kv.onnx",
    "g2p_encoder.onnx",
    "g2p_decoder.onnx",
    "weights.npz",
    "decode_state_init.npz",
    "tokenizer_ph.model",
)

_VOICE_FILES = {
    "female": "voices/female_narration.wav",
    "male": "voices/male_hello.wav",
    "news": "voices/male_news.wav",
}

_engine_cache: dict[str, Any] = {}


class PocketTTSProvider(TTSProvider):
    id = "pocket"
    title = "Pocket TTS Farsi v2"
    description = (
        "کیفیت بالاتر و کلون صدا (~۱۰۹M)، کاملاً آفلاین روی CPU با ONNX. "
        "یک‌بار مدل را با scripts/download_models.py --pocket بگیرید (~۴۷۰MB)."
    )
    offline = True
    license_note = "CC-BY-NC-4.0 — غیرتجاری مگر با مجوز"

    def _model_dir(self, settings: dict[str, Any]) -> Path:
        return Path(settings.get("pocket_model_dir", ""))

    def readiness(self, settings: dict[str, Any]) -> tuple[bool, str]:
        model_dir = self._model_dir(settings)
        if not model_dir.is_dir():
            return False, "پوشه مدل وجود ندارد. python scripts/download_models.py --pocket"
        missing = [name for name in _REQUIRED if not (model_dir / name).is_file()]
        if missing:
            return (
                False,
                "مدل Pocket ناقص است. اجرا کنید: python scripts/download_models.py --pocket "
                f"(کمبود: {', '.join(missing[:4])}{'…' if len(missing) > 4 else ''})",
            )
        voice = self._voice_path(settings)
        if not voice.is_file():
            return False, f"فایل صدای مرجع پیدا نشد: {voice}"
        return True, f"آماده · {model_dir.name}"

    def _voice_path(self, settings: dict[str, Any]) -> Path:
        model_dir = self._model_dir(settings)
        key = str(settings.get("pocket_voice") or "female")
        rel = _VOICE_FILES.get(key, _VOICE_FILES["female"])
        return model_dir / rel

    def _load(self, model_dir: Path):
        key = str(model_dir)
        if key in _engine_cache:
            return _engine_cache[key]
        from backend.pocket_engine.tts_onnx import OnnxTts

        engine = OnnxTts(pkg_dir=model_dir)
        _engine_cache[key] = engine
        return engine

    def _synth_sync(self, text: str, settings: dict[str, Any]) -> bytes:
        model_dir = self._model_dir(settings)
        engine = self._load(model_dir)
        voice = self._voice_path(settings)
        audio = engine.synthesize_text(text, str(voice), mode="split")
        if audio is None or len(audio) == 0:
            raise RuntimeError("خروجی Pocket TTS خالی بود.")
        pcm = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
        samples = (pcm * 32767.0).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(int(engine.sample_rate))
            wf.writeframes(samples.tobytes())
        return buf.getvalue()

    async def synthesize(self, text: str, settings: dict[str, Any]) -> TTSResult:
        ready, detail = self.readiness(settings)
        if not ready:
            raise RuntimeError(detail)
        audio = await asyncio.to_thread(self._synth_sync, text, settings)
        return TTSResult(
            audio=audio,
            media_type="audio/wav",
            provider=self.id,
            offline=True,
        )
