from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class TTSResult:
    audio: bytes
    media_type: str
    provider: str
    offline: bool


class TTSProvider(ABC):
    id: str
    title: str
    description: str
    offline: bool
    license_note: str = ""

    def meta(self, settings: dict[str, Any]) -> dict[str, Any]:
        ready, detail = self.readiness(settings)
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "offline": self.offline,
            "license_note": self.license_note,
            "ready": ready,
            "detail": detail,
        }

    @abstractmethod
    def readiness(self, settings: dict[str, Any]) -> tuple[bool, str]:
        ...

    @abstractmethod
    async def synthesize(self, text: str, settings: dict[str, Any]) -> TTSResult:
        ...
