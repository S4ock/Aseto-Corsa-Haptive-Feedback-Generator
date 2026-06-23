"""Fail-closed safety policy for an output-only haptics research application."""

OFFLINE_WARNING = "Use this only offline/single-player/time-trial. This tool does not modify gameplay inputs."
ALLOWED_GAMES = {"f1_25", "forza_horizon_5", "assetto_corsa", "mock"}
ALLOWED_OUTPUTS = {"stub", "dualsense"}


class SafetyError(RuntimeError):
    pass


def enforce_safe_mode(games_config: dict, game: str, output: str | None = None) -> None:
    """Validate the tiny allow-list before any telemetry or output connection."""
    if games_config.get("safe_mode") is not True:
        raise SafetyError("safe_mode must remain true; refusing to start.")
    if game not in ALLOWED_GAMES:
        raise SafetyError(f"Unsupported telemetry adapter: {game}")
    if output is not None and output not in ALLOWED_OUTPUTS:
        raise SafetyError(f"Unsupported output mode: {output}")


def print_startup_warning() -> None:
    print(f"WARNING: {OFFLINE_WARNING}")
