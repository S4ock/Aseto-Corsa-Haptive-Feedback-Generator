"""USB DualSense vibration output using Pygame's physical-controller rumble API.

This module sends vibration only. It never creates a virtual controller, reads
controller axes/buttons, or sends gameplay inputs. Adaptive triggers remain out
of scope for this portable output path because Pygame exposes no standard API
for them.
"""
from __future__ import annotations

import threading
from typing import Any

from .output_base import HapticOutput
from .output_stub import StubOutput


class DualSenseOutput(HapticOutput):
    def __init__(self, config: dict[str, Any] | None = None, pygame_module=None):
        config = config or {}
        self.name_contains = str(config.get("name_contains", "Wireless Controller")).lower()
        self.duration_ms = max(20, int(config.get("rumble_duration_ms", 120)))
        self._pygame = pygame_module
        self.joystick = None
        self.available = False
        self.fallback = StubOutput()
        self._rumble_failure_printed = False

    def connect(self) -> None:
        try:
            if self._pygame is None:
                import pygame
                self._pygame = pygame
            self._pygame.joystick.init()
            for index in range(self._pygame.joystick.get_count()):
                candidate = self._pygame.joystick.Joystick(index)
                if self.name_contains in candidate.get_name().lower():
                    self.joystick = candidate
                    self.available = True
                    print(f"DualSense vibration output connected: {candidate.get_name()}")
                    return
            print(f"No USB DualSense matching '{self.name_contains}' was found; using stub output.")
        except Exception as error:  # Optional hardware support must never stop telemetry.
            print(f"DualSense vibration output unavailable ({error}); using stub output.")
        self.fallback.connect()

    def send_feedback(self, feedback_dict: dict) -> None:
        if not self.available or self.joystick is None:
            self.fallback.send_feedback(feedback_dict)
            return
        low = _clamp(feedback_dict.get("vibration_left", 0.0))
        high = _clamp(feedback_dict.get("vibration_right", 0.0))
        # Pygame accepts left/right motor strengths and a short duration in ms.
        # A repeated low-latency command gives the runtime full telemetry control.
        try:
            if low == 0.0 and high == 0.0:
                self.joystick.stop_rumble()
            elif not self.joystick.rumble(low, high, self.duration_ms) and not self._rumble_failure_printed:
                self._rumble_failure_printed = True
                print("This controller/driver does not expose USB rumble through Pygame; using stub output.")
                self.available = False
                self.fallback.connect()
        except Exception as error:
            if not self._rumble_failure_printed:
                self._rumble_failure_printed = True
                print(f"USB rumble failed ({error}); using stub output.")
            self.available = False
            self.fallback.connect()

    def stop(self) -> None:
        if self.available and self.joystick is not None:
            try:
                self.joystick.stop_rumble()
            except Exception:
                pass

    def close(self) -> None:
        self.stop()
        if self.available and self.joystick is not None:
            try:
                self.joystick.quit()
            except Exception:
                pass


def _clamp(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


class DirectHidDualSenseOutput(HapticOutput):
    """Haptics-only backend using the physical DualSense HID device directly.

    No callbacks or controller state are registered/read by this application.
    The library's transport handles the device connection; this class only sets
    its left/right rumble output values and resets them on shutdown.
    """

    def __init__(self, config: dict[str, Any] | None = None, controller_class=None):
        config = config or {}
        self._controller_class = controller_class
        self.controller = None
        self.available = False
        self.fallback = StubOutput()
        self.keepalive_hz = max(20.0, min(250.0, float(config.get("rumble_keepalive_hz", 120))))
        self._left, self._right = 0.0, 0.0
        self._lock = threading.Lock()
        self._worker_stop = threading.Event()
        self._worker: threading.Thread | None = None

    def connect(self) -> None:
        try:
            if self._controller_class is None:
                from dualsense_controller import DualSenseController
                self._controller_class = DualSenseController
            devices = self._controller_class.enumerate_devices()
            if not devices:
                raise RuntimeError("No USB DualSense device was found")
            self.controller = self._controller_class(device_index_or_device_info=devices[0])
            self.controller.activate()
            self.available = True
            self._worker_stop.clear()
            self._worker = threading.Thread(target=self._keepalive_loop, name="dualsense-haptics", daemon=True)
            self._worker.start()
            print("Direct USB DualSense haptics connected.")
        except Exception as error:
            print(f"Direct USB DualSense haptics unavailable ({error}); using stub output.")
            self.fallback.connect()

    def send_feedback(self, feedback_dict: dict) -> None:
        if not self.available or self.controller is None:
            self.fallback.send_feedback(feedback_dict)
            return
        try:
            with self._lock:
                self._left = _clamp(feedback_dict.get("vibration_left", 0.0))
                self._right = _clamp(feedback_dict.get("vibration_right", 0.0))
            self._write_current_output()
        except Exception as error:
            print(f"Direct USB haptics failed ({error}); using stub output.")
            self.available = False
            self.fallback.connect()

    def stop(self) -> None:
        if self.available and self.controller is not None:
            try:
                with self._lock:
                    self._left, self._right = 0.0, 0.0
                self._write_current_output()
            except Exception:
                pass

    def close(self) -> None:
        self.stop()
        self._worker_stop.set()
        if self._worker is not None:
            self._worker.join(timeout=1.0)
            self._worker = None
        if self.available and self.controller is not None:
            try:
                self.controller.deactivate()
            except Exception:
                pass

    def _keepalive_loop(self) -> None:
        while not self._worker_stop.wait(1.0 / self.keepalive_hz):
            if not self.available:
                return
            try:
                self._write_current_output()
            except Exception:
                return

    def _write_current_output(self) -> None:
        if self.controller is None:
            return
        with self._lock:
            left, right = self._left, self._right
        self.controller.left_rumble.set(round(left * 255))
        self.controller.right_rumble.set(round(right * 255))


def _create_direct_hid(config: dict[str, Any]) -> HapticOutput:
    return DirectHidDualSenseOutput(config)


def create_output(mode: str, config: dict[str, Any] | None = None) -> HapticOutput:
    if mode == "stub":
        return StubOutput()
    config = config or {}
    return _create_direct_hid(config) if config.get("backend", "direct_hid") == "direct_hid" else DualSenseOutput(config)
