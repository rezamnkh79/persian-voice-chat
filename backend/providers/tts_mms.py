from __future__ import annotations

import asyncio
import io
import logging
import wave
from typing import Any

import numpy as np

from backend.providers.tts_base import TTSProvider, TTSResult

logger = logging.getLogger("voice")

_pipe_cache: dict[str, Any] = {}


class MMSTTSProvider(TTSProvider):
    id = "mms"
    title = "MMS-TTS Persian"
    description = (
        "مدل VITS فیسبوک (facebook/mms-tts-fas). کیفیت خوب ولی سنگین‌تر "
        "(نیاز به PyTorch + transformers). کاملاً محلی."
    )
    offline = True
    license_note = "CC-BY-NC-4.0 — برای استفاده تجاری بدون مجوز مناسب نیست"

    def readiness(self, settings: dict[str, Any]) -> tuple[bool, str]:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except Exception:
            return (
                False,
                "برای فعال‌سازی: pip install torch transformers accelerate",
            )
        return True, "وابستگی‌ها نصب‌اند (اولین اجرا مدل را دانلود می‌کند)"

    def _load(self, model_id: str):
        if model_id in _pipe_cache:
            return _pipe_cache[model_id]
        import torch
        from transformers import VitsModel, AutoTokenizer

        model = VitsModel.from_pretrained(model_id)
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model.eval()
        bundle = {"model": model, "tokenizer": tokenizer, "torch": torch}
        _pipe_cache[model_id] = bundle
        return bundle

    def _synth_sync(self, text: str, settings: dict[str, Any]) -> bytes:
        model_id = str(settings.get("mms_model_id") or "facebook/mms-tts-fas")
        bundle = self._load(model_id)
        torch = bundle["torch"]
        inputs = bundle["tokenizer"](text, return_tensors="pt")
        with torch.no_grad():
            output = bundle["model"](**inputs).waveform
        audio = output.squeeze().cpu().numpy()
        # float32 -1..1 -> int16 wav
        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767.0).astype(np.int16)
        sr = int(getattr(bundle["model"].config, "sampling_rate", 16000))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
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
