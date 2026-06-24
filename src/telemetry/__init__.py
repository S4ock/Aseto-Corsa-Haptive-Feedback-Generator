from .assetto_corsa import AssettoCorsaAdapter
from .f1_25_udp import F125UdpAdapter
from .forza_horizon_5_udp import ForzaHorizon5UdpAdapter
from .mock_telemetry import MockTelemetryAdapter
from .outgauge_udp import BeamNGDriveOutGaugeAdapter, LiveForSpeedOutGaugeAdapter


def create_adapter(game: str, config: dict, session_id: str):
    adapters = {
        "mock": MockTelemetryAdapter,
        "f1_25": F125UdpAdapter,
        "forza_horizon_5": ForzaHorizon5UdpAdapter,
        "assetto_corsa": AssettoCorsaAdapter,
        "beamng_drive": BeamNGDriveOutGaugeAdapter,
        "live_for_speed": LiveForSpeedOutGaugeAdapter,
    }
    return adapters[game](config.get(game, {}), session_id=session_id)
