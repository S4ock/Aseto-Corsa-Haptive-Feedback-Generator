from src.utils.session_names import next_session_name


def test_next_session_name_starts_at_default_when_no_recordings_exist(tmp_path):
    assert next_session_name("session_001", tmp_path) == "session_001"


def test_next_session_name_advances_from_saved_recordings_and_preserves_prefix(tmp_path):
    raw = tmp_path / "data" / "raw"
    processed = tmp_path / "data" / "processed"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    (raw / "f1_run_007_raw.jsonl").touch()
    (processed / "f1_run_009_processed.csv").touch()
    assert next_session_name("f1_run_001", tmp_path) == "f1_run_010"


def test_next_session_name_advances_after_a_manually_edited_name(tmp_path):
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    (raw / "my_lap_042_metadata.json").touch()
    assert next_session_name("my_lap_042", tmp_path) == "my_lap_043"
