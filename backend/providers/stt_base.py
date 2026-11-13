from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class STTResult:
    text: str
    provider: str
    offline: bool
    duration: float | None = None


class STTProvider(ABC):
    id: str
    title: str
    description: str
    offline: bool
    client_side: bool = False

    def meta(self, settings: dict[str, Any]) -> dict[str, Any]:
        ready, detail = self.readiness(settings)
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "offline": self.offline,
            "client_side": self.client_side,
            "ready": ready,
            "detail": detail,
        }

    @abstractmethod
    def readiness(self, settings: dict[str, Any]) -> tuple[bool, str]:
        ...

    @abstractmethod
    async def transcribe(self, wav_path: Path, settings: dict[str, Any]) -> STTResult:
        ...
