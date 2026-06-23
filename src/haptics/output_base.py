from abc import ABC, abstractmethod


class HapticOutput(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def send_feedback(self, feedback_dict: dict) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
