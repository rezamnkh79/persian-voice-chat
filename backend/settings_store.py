"""Persistent app settings (JSON on disk)."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "data" / "settings.json"
MODELS_DIR = ROOT / "models"

DEFAULT_SETTINGS: dict[str, Any] = {
    "tts_provider": "piper_mana",
    "stt_provider": "vosk",
    "edge_voice": "female",
    "piper_model_path": str(
        MODELS_DIR / "Mana-Persian-Piper" / "fa_IR-mana-medium.onnx"
    ),
    "piper_length_scale": 1.0,
    "vosk_model_path": str(MODELS_DIR / "vosk-model-small-fa-0.42"),
    "mms_model_id": "facebook/mms-tts-fas",
    "pocket_model_dir": str(MODELS_DIR / "pocket-tts-farsi"),
    "pocket_voice": "female",
    "stt_language": "fa-IR",
}

_lock = threading.RLock()
_cache: dict[str, Any] | None = None


def _ensure_parent() -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict[str, Any]:
    global _cache
    with _lock:
        if _cache is not None:
            return deepcopy(_cache)
        data = deepcopy(DEFAULT_SETTINGS)
        if SETTINGS_PATH.exists():
            try:
                saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    data.update({k: v for k, v in saved.items() if k in DEFAULT_SETTINGS})
            except Exception:
                pass
        _cache = data
        return deepcopy(data)


def save_settings(updates: dict[str, Any]) -> dict[str, Any]:
    global _cache
    with _lock:
        current = load_settings()
        for key, value in updates.items():
            if key in DEFAULT_SETTINGS:
                current[key] = value
        _ensure_parent()
        SETTINGS_PATH.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _cache = current
        return deepcopy(current)


def reset_settings() -> dict[str, Any]:
    global _cache
    with _lock:
        _cache = None
        if SETTINGS_PATH.exists():
            SETTINGS_PATH.unlink()
        return load_settings()
