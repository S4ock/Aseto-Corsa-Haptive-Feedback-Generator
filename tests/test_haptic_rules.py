from src.constants import HAPTIC_COLUMNS
from src.haptics.haptic_rules import HapticRuleEngine


def test_haptic_rule_outputs_are_bounded():
    engine = HapticRuleEngine({})
    feedback = engine.label({"brake": 1, "throttle": 1, "wheel_slip_fl": 2, "wheel_slip_fr": 2, "wheel_slip_rl": 2, "wheel_slip_rr": 2, "rpm": 12000, "max_rpm": 10000, "on_track": False, "collision_intensity": 2, "accel_y": 100})
    assert all(0 <= feedback[column] <= 1 for column in HAPTIC_COLUMNS)
    assert feedback["haptic_event"] == "collision"
