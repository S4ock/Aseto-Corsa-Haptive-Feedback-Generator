from .assetto_corsa import AssettoCorsaAdapter
from .f1_25_udp import F125UdpAdapter
from .forza_horizon_5_udp import ForzaHorizon5UdpAdapter
from .mock_telemetry import MockTelemetryAdapter


def create_adapter(game: str, config: dict, session_id: str):
    adapters = {
        "mock": MockTelemetryAdapter,
        "f1_25": F125UdpAdapter,
        "forza_horizon_5": ForzaHorizon5UdpAdapter,
        "assetto_corsa": AssettoCorsaAdapter,
    }
    return adapters[game](config.get(game, {}), session_id=session_id)
