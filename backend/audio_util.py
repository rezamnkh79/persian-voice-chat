"""Shared audio helpers."""

from __future__ import annotations

import io
import logging
import shutil
import subprocess
import wave
from pathlib import Path

logger = logging.getLogger("voice")


def resolve_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        logger.warning("ffmpeg unavailable: %s", exc)
        return None


FFMPEG_BIN = resolve_ffmpeg()
if FFMPEG_BIN:
    logger.info("ffmpeg ready: %s", FFMPEG_BIN)


def convert_to_wav(src: Path, dst: Path) -> None:
    if not FFMPEG_BIN:
        raise RuntimeError("ffmpeg پیدا نشد.")
    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
        raise RuntimeError(result.stderr.strip() or "تبدیل صوت ناموفق بود.")


def wav_duration_seconds(data: bytes) -> float:
    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate) if rate else 0.0
    except Exception:
        return 0.0
