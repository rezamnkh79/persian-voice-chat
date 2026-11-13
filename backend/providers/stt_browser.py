from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.providers.stt_base import STTProvider, STTResult


class BrowserSTTProvider(STTProvider):
    """
    Marker provider: actual recognition runs in the browser via Web Speech API.
    Server refuses audio uploads when this is selected.
    """

    id = "browser"
    title = "مرورگر (Web Speech)"
    description = (
        "تشخیص گفتار داخل مرورگر (Chrome/Edge با fa-IR). "
        "بدون بار روی سرور؛ معمولاً نیاز به اینترنت دارد."
    )
    offline = False
    client_side = True

    def readiness(self, settings: dict[str, Any]) -> tuple[bool, str]:
        return True, "روی کلاینت اجرا می‌شود"

    async def transcribe(self, wav_path: Path, settings: dict[str, Any]) -> STTResult:
        raise RuntimeError(
            "ارائه‌دهنده «مرورگر» روی سرور صوت پردازش نمی‌کند. "
            "از میکروفون در داشبورد استفاده کنید یا STT را به Vosk/Google تغییر دهید."
        )
