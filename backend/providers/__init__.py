"""TTS / STT provider registry."""

from __future__ import annotations

from typing import Any

from backend.providers.stt_base import STTProvider
from backend.providers.stt_browser import BrowserSTTProvider
from backend.providers.stt_google import GoogleSTTProvider
from backend.providers.stt_vosk import VoskSTTProvider
from backend.providers.tts_base import TTSProvider
from backend.providers.tts_edge import EdgeTTSProvider
from backend.providers.tts_mms import MMSTTSProvider
from backend.providers.tts_piper import PiperManaTTSProvider
from backend.providers.tts_pocket import PocketTTSProvider

TTS_PROVIDERS: dict[str, TTSProvider] = {
    p.id: p
    for p in (
        PiperManaTTSProvider(),
        EdgeTTSProvider(),
        MMSTTSProvider(),
        PocketTTSProvider(),
    )
}

STT_PROVIDERS: dict[str, STTProvider] = {
    p.id: p
    for p in (
        VoskSTTProvider(),
        GoogleSTTProvider(),
        BrowserSTTProvider(),
    )
}


def list_tts_meta(settings: dict[str, Any]) -> list[dict[str, Any]]:
    return [p.meta(settings) for p in TTS_PROVIDERS.values()]


def list_stt_meta(settings: dict[str, Any]) -> list[dict[str, Any]]:
    return [p.meta(settings) for p in STT_PROVIDERS.values()]


def get_tts(provider_id: str) -> TTSProvider:
    if provider_id not in TTS_PROVIDERS:
        raise KeyError(provider_id)
    return TTS_PROVIDERS[provider_id]


def get_stt(provider_id: str) -> STTProvider:
    if provider_id not in STT_PROVIDERS:
        raise KeyError(provider_id)
    return STT_PROVIDERS[provider_id]
