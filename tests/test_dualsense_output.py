from src.haptics.dualsense_output import DualSenseOutput


class FakeJoystick:
    def __init__(self): self.commands = []
    def get_name(self): return "Wireless Controller"
    def rumble(self, low, high, duration): self.commands.append((low, high, duration)); return True
    def stop_rumble(self): self.commands.append(("stop",))
    def quit(self): pass


class FakeJoystickModule:
    def __init__(self, joystick): self.device = joystick
    def init(self): pass
    def get_count(self): return 1
    def Joystick(self, _index): return self.device


class FakePygame:
    def __init__(self, joystick): self.joystick = FakeJoystickModule(joystick)


def test_usb_output_sends_only_rumble_strengths():
    device = FakeJoystick()
    output = DualSenseOutput({"name_contains": "wireless controller", "rumble_duration_ms": 100}, pygame_module=FakePygame(device))
    output.connect()
    output.send_feedback({"vibration_left": .2, "vibration_right": .8})
    output.stop()
    assert device.commands == [(.2, .8, 100), ("stop",)]
