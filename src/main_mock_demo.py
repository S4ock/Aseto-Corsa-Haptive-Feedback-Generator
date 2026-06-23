"""One command to record mock data, train, then run safe stub predictions."""
from src.main_recorder import record_session
from src.main_runtime import run_runtime
from src.training.dataset_builder import load_processed_sessions
from src.training.train_models import train
from src.utils.config_loader import load_yaml


def main() -> None:
    for number in range(1, 4):
        record_session("mock", f"mock_demo_{number:03d}", max_packets=90)
    config = load_yaml("training.yaml")
    config["models"] = ["random_forest", "hist_gradient_boosting", "mlp"]
    metrics = train(load_processed_sessions(), config)
    print(f"Demo model: {metrics['best_model']}")
    run_runtime("mock", "models/best_model.pkl", "stub", max_packets=20)


if __name__ == "__main__":
    main()
