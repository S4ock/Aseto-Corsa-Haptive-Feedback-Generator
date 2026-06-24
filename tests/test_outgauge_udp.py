import struct

from src.telemetry.outgauge_udp import OUTGAUGE, BeamNGDriveOutGaugeAdapter, LiveForSpeedOutGaugeAdapter


def _packet():
    return OUTGAUGE.pack(1234, b"CAR\0", 0, 3, 0, 20.0, 6500.0, 0.0, 90.0, .5, 1.0, 100.0, 0, 0, .75, .25, 0.0, b"\0" * 16, b"\0" * 16)


def test_outgauge_adapters_decode_documented_speed_and_controls(monkeypatch):
    adapter = BeamNGDriveOutGaugeAdapter({"max_rpm": 8000}, "s1")
    class Socket:
        def recvfrom(self, _): return _packet(), ("127.0.0.1", 1)
    adapter.socket = Socket()
    packet = adapter.read_packet()
    row = adapter.normalize_packet(packet)
    assert row["game"] == "beamng_drive" and row["speed_kmh"] == 72.0
    assert row["rpm"] == 6500.0 and row["throttle"] == .75 and row["brake"] == .25
    assert LiveForSpeedOutGaugeAdapter({}, "s2").game == "live_for_speed"
