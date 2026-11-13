"""Persian text normalization helpers."""

from __future__ import annotations


def normalize_persian_text(text: str) -> str:
    replacements = {
        "ك": "ک",
        "ي": "ی",
        "ى": "ی",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "\u200f": "",
        "\u200e": "",
    }
    out = text.strip()
    for src, dst in replacements.items():
        out = out.replace(src, dst)
    out = " ".join(out.split())
    return out
