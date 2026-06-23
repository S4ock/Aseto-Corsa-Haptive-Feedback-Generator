from src.haptics.dualsense_output import DirectHidDualSenseOutput


class Value:
    def __init__(self): self.values = []
    def set(self, value): self.values.append(value)


class TriggerEffect:
    def __init__(self): self.calls = []
    def feedback(self, start_position, strength): self.calls.append(("feedback", start_position, strength))
    def off(self): self.calls.append(("off",))


class Trigger:
    def __init__(self): self.effect = TriggerEffect()


class FakeDirectController:
    @classmethod
    def enumerate_devices(cls): return ["device"]
    def __init__(self, device_index_or_device_info):
        self.left_rumble, self.right_rumble = Value(), Value()
        self.left_trigger, self.right_trigger = Trigger(), Trigger()
        self.activated = False
    def activate(self): self.activated = True
    def deactivate(self): self.activated = False


def test_direct_hid_output_sets_rumble_and_output_only_trigger_resistance():
    output = DirectHidDualSenseOutput({"rumble_keepalive_hz": 20}, controller_class=FakeDirectController)
    output.connect()
    output.send_feedback({"vibration_left": .25, "vibration_right": .75, "left_trigger_resistance": .5, "right_trigger_resistance": 1.0})
    output.stop()
    assert 64 in output.controller.left_rumble.values
    assert 191 in output.controller.right_rumble.values
    assert output.controller.left_rumble.values[-1] == 0
    assert output.controller.right_rumble.values[-1] == 0
    assert ("feedback", 1, 5) in output.controller.left_trigger.effect.calls
    assert ("feedback", 1, 8) in output.controller.right_trigger.effect.calls
    assert output.controller.left_trigger.effect.calls[-1] == ("off",)
    assert output.controller.right_trigger.effect.calls[-1] == ("off",)
