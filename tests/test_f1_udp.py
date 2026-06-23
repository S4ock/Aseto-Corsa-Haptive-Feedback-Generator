import struct

import pytest

from src.telemetry.f1_25_udp import CAR_TELEMETRY, HEADER, F125UdpAdapter


def test_f1_2026_car_telemetry_packet_decodes_player_car():
    header = HEADER.pack(2026, 26, 1, 0, 1, 6, 99, 12.5, 1, 1, 0, 255)
    car = CAR_TELEMETRY.pack(
        287, .75, -.2, .4, 10, 6, 11200, 0, 80, 0,
        400, 401, 402, 403, 90, 91, 92, 93, 80, 81, 82, 83, 110,
        22.0, 22.1, 22.2, 22.3, 0, 0, 0, 0,
    )
    adapter = F125UdpAdapter({"udp_format": 2026}, "test")
    adapter.expected_format, adapter.max_rpm, adapter._format_warning_printed = 2026, 15000, False
    class Socket:
        def recvfrom(self, _size): return header + car + (b"\0" * (CAR_TELEMETRY.size * 21 + 3)), ("127.0.0.1", 20777)
    adapter.socket = Socket()
    packet = adapter.read_packet()
    assert packet["speed_kmh"] == 287
    assert packet["rpm"] == 11200
    assert packet["throttle"] == pytest.approx(.75)
    assert packet["brake"] == pytest.approx(.4)
    assert packet["surface_type"] == "tarmac"


def test_f1_collision_event_marks_following_telemetry_samples():
    header = HEADER.pack(2026, 26, 1, 0, 1, 3, 99, 12.5, 1, 1, 0, 255)
    collision = header + b"COLL" + bytes([0, 5])
    telemetry_header = HEADER.pack(2026, 26, 1, 0, 1, 6, 99, 12.6, 2, 2, 0, 255)
    car = CAR_TELEMETRY.pack(200, .5, 0, 0, 0, 5, 9000, 0, 0, 0, *([0] * 4), *([80] * 4), *([80] * 4), 100, *([20.0] * 4), *([0] * 4))
    adapter = F125UdpAdapter({"udp_format": 2026}, "test")
    adapter.expected_format, adapter.max_rpm, adapter._format_warning_printed = 2026, 15000, False
    class Socket:
        def __init__(self): self.packets = [collision, telemetry_header + car + (b"\0" * (CAR_TELEMETRY.size * 21 + 3))]
        def recvfrom(self, _size): return self.packets.pop(0), ("127.0.0.1", 20777)
    adapter.socket = Socket()
    assert adapter.read_packet() is None
    assert adapter.read_packet()["collision_intensity"] == 1.0
