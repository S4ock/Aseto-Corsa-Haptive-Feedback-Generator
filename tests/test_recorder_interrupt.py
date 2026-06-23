import json

import pandas as pd

import src.main_recorder as recorder


class InterruptingAdapter:
    def __init__(self):
        self.reads = 0

    def connect(self): pass
    def close(self): pass

    def read_packet(self):
        self.reads += 1
        if self.reads == 1:
            return {"timestamp": 1, "speed_kmh": 100, "rpm": 6000, "max_rpm": 15000, "throttle": .5, "brake": 0, "steering": 0}
        raise KeyboardInterrupt

    def normalize_packet(self, packet):
        return {"timestamp": packet["timestamp"], "game": "mock", "session_id": "interrupt_test", "speed_kmh": packet["speed_kmh"], "rpm": packet["rpm"], "max_rpm": packet["max_rpm"], "throttle": packet["throttle"], "brake": packet["brake"], "steering": packet["steering"]}


def test_ctrl_c_saves_recorded_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(recorder, "ROOT", tmp_path)
    monkeypatch.setattr(recorder, "load_yaml", lambda name: {"safe_mode": True, "recorder": {"max_packets": 50, "timeout_seconds": 10}, "mock": {}} if name == "games.yaml" else {})
    monkeypatch.setattr(recorder, "create_adapter", lambda *args: InterruptingAdapter())
    raw_path, processed_path = recorder.record_session("mock", "interrupt_test")
    assert raw_path.exists() and processed_path.exists()
    assert len(pd.read_csv(processed_path)) == 1
    metadata = json.loads((tmp_path / "data/raw/interrupt_test_metadata.json").read_text())
    assert metadata["stopped_by_user"] is True
