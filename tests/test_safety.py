import pytest

from src.utils.safety import SafetyError, enforce_safe_mode


def test_safe_mode_blocks_non_haptic_output_behavior():
    with pytest.raises(SafetyError):
        enforce_safe_mode({"safe_mode": True}, "mock", "virtual_controller")
    with pytest.raises(SafetyError):
        enforce_safe_mode({"safe_mode": False}, "mock", "stub")
