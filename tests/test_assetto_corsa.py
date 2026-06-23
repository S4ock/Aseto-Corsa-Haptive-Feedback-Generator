import struct

import pytest

from src.telemetry.assetto_corsa import AssettoCorsaAdapter, PHYSICS_MIN_SIZE


def test_assetto_physics_fields_normalize_without_game_process_access():
    data = bytearray(PHYSICS_MIN_SIZE)
    struct.pack_into("<i", data, 0, 1)
    struct.pack_into("<3f", data, 4, .7, .3, 10.0)
    struct.pack_into("<2i", data, 16, 4, 7000)
    struct.pack_into("<2f", data, 24, .3, 150.0)
    struct.pack_into("<3f", data, 32, 40, 1, 0)
    struct.pack_into("<3f", data, 44, 1, 0, 1)
    struct.pack_into("<4f", data, 56, .1, .2, .3, .4)
    struct.pack_into("<4f", data, 152, 80, 81, 82, 83)
    adapter = AssettoCorsaAdapter({"max_rpm": 9000}, "ac_test")
    adapter.view, adapter.last_packet_id, adapter.max_rpm, adapter.max_steering_angle, adapter.slip_scale = None, None, 9000, .6, 1.0
    # Reuse the parser's source-independent code path with a one-shot byte buffer.
    class Reader:
        def __call__(self, _view, _size): return bytes(data)
    import src.telemetry.assetto_corsa as module
    original = module.ctypes.string_at
    module.ctypes.string_at = Reader()
    try:
        adapter.view = object()
        packet = adapter.read_packet()
    finally:
        module.ctypes.string_at = original
    assert packet["speed_kmh"] == 150
    assert packet["rpm"] == 7000
    assert packet["wheel_slip_rr"] == pytest.approx(.4)


def test_assetto_damage_increase_creates_short_collision_signal():
    data = bytearray(PHYSICS_MIN_SIZE)
    struct.pack_into("<i", data, 0, 1)
    adapter = AssettoCorsaAdapter({"collision_damage_delta_threshold": .01}, "ac_test")
    adapter.view, adapter.last_packet_id, adapter.max_rpm, adapter.max_steering_angle, adapter.slip_scale = object(), None, 9000, .6, 1.0
    adapter.damage_delta_threshold, adapter.previous_damage, adapter._collision_packets_remaining, adapter._collision_strength = .01, None, 0, 0.0
    import src.telemetry.assetto_corsa as module
    original = module.ctypes.string_at
    module.ctypes.string_at = lambda _view, _size: bytes(data)
    try:
        assert adapter.read_packet()["collision_intensity"] == 0.0
        struct.pack_into("<i", data, 0, 2)
        struct.pack_into("<f", data, 224, .02)
        assert adapter.read_packet()["collision_intensity"] == 1.0
    finally:
        module.ctypes.string_at = original
