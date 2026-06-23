from src.haptics.dualsense_output import DirectHidDualSenseOutput


class Value:
    def __init__(self): self.values = []
    def set(self, value): self.values.append(value)


class FakeDirectController:
    @classmethod
    def enumerate_devices(cls): return ["device"]
    def __init__(self, device_index_or_device_info):
        self.left_rumble, self.right_rumble = Value(), Value()
        self.activated = False
    def activate(self): self.activated = True
    def deactivate(self): self.activated = False


def test_direct_hid_output_sets_only_rumble_values():
    output = DirectHidDualSenseOutput({"rumble_keepalive_hz": 20}, controller_class=FakeDirectController)
    output.connect()
    output.send_feedback({"vibration_left": .25, "vibration_right": .75})
    output.stop()
    assert 64 in output.controller.left_rumble.values
    assert 191 in output.controller.right_rumble.values
    assert output.controller.left_rumble.values[-1] == 0
    assert output.controller.right_rumble.values[-1] == 0
