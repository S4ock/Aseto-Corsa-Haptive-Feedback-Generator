from src.training.dataset_builder import load_processed_sessions
from src.training.train_models import train
from src.utils.config_loader import load_yaml
from src.utils.safety import enforce_safe_mode, print_startup_warning


def main() -> None:
    games = load_yaml("games.yaml")
    enforce_safe_mode(games, "mock")
    print_startup_warning()
    metrics = train(load_processed_sessions(), load_yaml("training.yaml"))
    print(f"Training complete. Best model: {metrics['best_model']} (MAE {metrics['mae']:.4f})")


if __name__ == "__main__":
    main()
