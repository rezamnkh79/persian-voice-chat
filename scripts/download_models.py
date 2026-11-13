#!/usr/bin/env python3
"""Download offline models into ./models (safe to re-run; skips complete files)."""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import requests
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
MANA_DIR = MODELS / "Mana-Persian-Piper"
VOSK_DIR = MODELS / "vosk-model-small-fa-0.42"
POCKET_DIR = MODELS / "pocket-tts-farsi"
VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-fa-0.42.zip"
VOICE_BASE = "https://raw.githubusercontent.com/nimaone/persian_tts/main/voices"

POCKET_ONNX_FILES = (
    "manifest.json",
    "decode_state_init.npz",
    "flow_lm_step.onnx",
    "flow_lm_step.onnx.data",
    "g2p_decoder.onnx",
    "g2p_decoder.onnx.data",
    "g2p_encoder.onnx",
    "mimi_decoder_step_kv.onnx",
    "mimi_decoder_step_kv.onnx.data",
    "mimi_encoder.onnx",
    "mimi_encoder.onnx.data",
    "weights.npz",
)

# Minimum bytes so LFS pointer files (~130B) are treated as incomplete.
POCKET_MIN_SIZE = {
    "manifest.json": 500,
    "decode_state_init.npz": 1_000_000,
    "flow_lm_step.onnx": 100_000,
    "flow_lm_step.onnx.data": 300_000_000,
    "g2p_decoder.onnx": 100_000,
    "g2p_decoder.onnx.data": 10_000_000,
    "g2p_encoder.onnx": 1_000_000,
    "mimi_decoder_step_kv.onnx": 100_000,
    "mimi_decoder_step_kv.onnx.data": 10_000_000,
    "mimi_encoder.onnx": 100_000,
    "mimi_encoder.onnx.data": 10_000_000,
    "weights.npz": 1_000_000,
    "tokenizer_ph.model": 10_000,
    "normalize_fa.py": 200,
}


def _ok(path: Path, min_size: int) -> bool:
    return path.is_file() and path.stat().st_size >= min_size


def _hf(repo: str, filename: str, dest_dir: Path, min_size: int) -> Path:
    dest = dest_dir / filename
    if _ok(dest, min_size):
        print(f"  skip {filename} ({dest.stat().st_size} bytes)")
        return dest
    if dest.exists():
        dest.unlink()
    print(f"  get  {filename} ...")
    path = Path(
        hf_hub_download(
            repo_id=repo,
            filename=filename,
            local_dir=str(dest_dir),
        )
    )
    if path.stat().st_size < min_size:
        raise RuntimeError(
            f"{filename} incomplete ({path.stat().st_size} bytes, need >= {min_size})"
        )
    print(f"  ok   {filename} ({path.stat().st_size} bytes)")
    return path


def download_mana() -> None:
    print("== Mana Persian Piper ==")
    MANA_DIR.mkdir(parents=True, exist_ok=True)
    _hf("MahtaFetrat/Mana-Persian-Piper", "fa_IR-mana-medium.onnx", MANA_DIR, 10_000_000)
    _hf("MahtaFetrat/Mana-Persian-Piper", "fa_IR-mana-medium.onnx.json", MANA_DIR, 1000)


def download_vosk() -> None:
    print("== Vosk Persian ==")
    if (VOSK_DIR / "am").exists() and (VOSK_DIR / "conf").exists():
        print(f"  skip already present: {VOSK_DIR}")
        return
    MODELS.mkdir(parents=True, exist_ok=True)
    print("  get  vosk-model-small-fa-0.42.zip ...")
    resp = requests.get(VOSK_URL, timeout=180)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(MODELS)
    print(f"  ok   {VOSK_DIR}")


def download_pocket() -> None:
    print("== Pocket TTS Farsi v2 ONNX (~470MB) ==")
    POCKET_DIR.mkdir(parents=True, exist_ok=True)
    for name in POCKET_ONNX_FILES:
        _hf(
            "Nimaone/pocket-tts-farsi-v2-onnx",
            name,
            POCKET_DIR,
            POCKET_MIN_SIZE.get(name, 1),
        )
    for name in ("tokenizer_ph.model", "normalize_fa.py"):
        _hf(
            "mehdi-hf/pocket-tts-farsi-v2",
            name,
            POCKET_DIR,
            POCKET_MIN_SIZE.get(name, 1),
        )

    voice_dir = POCKET_DIR / "voices"
    voice_dir.mkdir(parents=True, exist_ok=True)
    for name in ("female_narration.wav", "male_hello.wav", "male_news.wav"):
        dest = voice_dir / name
        if _ok(dest, 50_000):
            print(f"  skip voices/{name}")
            continue
        url = f"{VOICE_BASE}/{name}"
        print(f"  get  voices/{name} ...")
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        print(f"  ok   voices/{name} ({dest.stat().st_size} bytes)")
    print(f"Pocket ready: {POCKET_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Mana + Vosk + Pocket")
    parser.add_argument("--pocket", action="store_true", help="also download Pocket TTS")
    parser.add_argument("--only-pocket", action="store_true", help="download only Pocket TTS")
    parser.add_argument("--only-mana", action="store_true")
    parser.add_argument("--only-vosk", action="store_true")
    args = parser.parse_args()

    if args.only_pocket:
        download_pocket()
    elif args.only_mana:
        download_mana()
    elif args.only_vosk:
        download_vosk()
    else:
        download_mana()
        download_vosk()
        if args.pocket or args.all:
            download_pocket()
    print("Done.")
