from src.haptics.mixer import RuntimeHapticMixer


def test_mixer_applies_engine_floor_and_smooth_release():
    mixer = RuntimeHapticMixer({"runtime_mixer": {"engine_gain": .2, "moving_vibration_floor": .04, "attack_ms": 40, "release_ms": 200}})
    first = mixer.apply({"speed_kmh": 100, "rpm": 8000, "max_rpm": 10000}, {"vibration_left": 0, "vibration_right": 0}, now=1.0)
    second = mixer.apply({"speed_kmh": 0, "rpm": 0, "max_rpm": 10000}, {"vibration_left": 0, "vibration_right": 0}, now=1.01)
    assert first["vibration_left"] > 0
    assert 0 < second["vibration_left"] < first["vibration_left"]
