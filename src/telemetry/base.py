from abc import ABC, abstractmethod
from typing import Any


class TelemetryAdapter(ABC):
    """Read-only boundary around an official telemetry source."""

    def __init__(self, config: dict[str, Any], session_id: str):
        self.config = config
        self.session_id = session_id

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def read_packet(self) -> dict[str, Any] | None: ...

    @abstractmethod
    def normalize_packet(self, packet: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def close(self) -> None: ...
