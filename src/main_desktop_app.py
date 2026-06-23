"""Downloadable desktop workspace for recording, training, and live haptics."""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.main_recorder import record_session
from src.main_runtime import run_runtime
from src.training.dataset_builder import load_processed_sessions
from src.training.train_models import torch, train
from src.utils.config_loader import RESOURCE_ROOT, ROOT, load_yaml
from src.utils.safety import OFFLINE_WARNING


class HapticsDesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TelemetryDualSenseAI")
        self.root.resizable(False, False)
        self.messages: queue.Queue[str] = queue.Queue()
        self.stop_event: threading.Event | None = None
        self.worker: threading.Thread | None = None
        self.task = tk.StringVar(value="idle")
        self.game = tk.StringVar(value="assetto_corsa")
        self.session = tk.StringVar(value="session_001")
        default_model = RESOURCE_ROOT / "models" / "best_model.pkl"
        self.model = tk.StringVar(value=str(default_model if default_model.exists() else ROOT / "models" / "best_model.pkl"))
        self.state = tk.StringVar(value="Ready. Start an offline driving session, then choose an action.")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._poll_messages()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="TelemetryDualSenseAI", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Record telemetry, train a model, and run custom USB DualSense vibration.").grid(row=1, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text=OFFLINE_WARNING, foreground="#9c1c1c", wraplength=510).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 14))
        ttk.Label(frame, text="Game").grid(row=3, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=self.game, values=("assetto_corsa", "f1_25"), state="readonly", width=30).grid(row=3, column=1, columnspan=2, sticky="ew", padx=(10, 0))
        ttk.Label(frame, text="Session name").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.session, width=34).grid(row=4, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(8, 0))
        ttk.Label(frame, text="Trained model").grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.model, width=42).grid(row=5, column=1, sticky="ew", padx=(10, 8), pady=(8, 0))
        ttk.Button(frame, text="Browse…", command=self._browse).grid(row=5, column=2, pady=(8, 0))
        self.record_button = ttk.Button(frame, text="Start recording", command=self._start_recording)
        self.record_button.grid(row=6, column=0, sticky="ew", pady=(18, 0))
        self.train_button = ttk.Button(frame, text="Train model", command=self._start_training)
        self.train_button.grid(row=6, column=1, sticky="ew", padx=8, pady=(18, 0))
        self.runtime_button = ttk.Button(frame, text="Start haptics", command=self._start_runtime)
        self.runtime_button.grid(row=6, column=2, sticky="ew", pady=(18, 0))
        self.stop_button = ttk.Button(frame, text="Stop current action", command=self._stop, state="disabled")
        self.stop_button.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Label(frame, textvariable=self.state, wraplength=510).grid(row=8, column=0, columnspan=3, sticky="w", pady=(14, 6))
        self.log = tk.Text(frame, width=74, height=10, state="disabled", wrap="word")
        self.log.grid(row=9, column=0, columnspan=3, sticky="ew")
        ttk.Label(frame, text="Recording and haptics run until Stop. Training completes automatically. This app never sends gameplay inputs.", foreground="#555555", wraplength=510).grid(row=10, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _browse(self) -> None:
        filename = filedialog.askopenfilename(title="Choose trained model", initialdir=ROOT / "models", filetypes=[("Model", "*.pkl")])
        if filename:
            self.model.set(filename)

    def _begin(self, task: str, target, *args) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        self.task.set(task)
        self.stop_event = threading.Event()
        self.record_button.configure(state="disabled")
        self.train_button.configure(state="disabled")
        self.runtime_button.configure(state="disabled")
        self.stop_button.configure(state="normal" if task != "training" else "disabled")
        self.worker = threading.Thread(target=target, args=args, name=f"desktop-{task}", daemon=True)
        self.worker.start()

    def _start_recording(self) -> None:
        name = self.session.get().strip()
        if not name:
            messagebox.showerror("Session name required", "Enter a unique session name first.")
            return
        self.state.set("Recording telemetry…")
        self._begin("recording", self._record_worker, self.game.get(), name)

    def _record_worker(self, game: str, session: str) -> None:
        try:
            _, processed = record_session(game, session, stop_event=self.stop_event)
            self.messages.put(f"Saved recording: {processed}")
        except Exception as error:
            self.messages.put(f"ERROR: {error}")
        finally:
            self.messages.put("__STOPPED__")

    def _start_training(self) -> None:
        self.state.set("Training models… this can take a while on larger datasets.")
        self._begin("training", self._train_worker)

    def _train_worker(self) -> None:
        try:
            config = load_yaml("training.yaml")
            if torch is None:
                config["models"] = [name for name in config.get("models", []) if name != "torch_deep_mlp"]
                self.messages.put("CUDA PyTorch is not bundled; training the included CPU models instead.")
            metrics = train(load_processed_sessions(), config)
            self.messages.put(f"Training complete. Best model: {metrics['best_model']}; MAE: {metrics['mae']:.4f}")
        except Exception as error:
            self.messages.put(f"ERROR: {error}")
        finally:
            self.messages.put("__STOPPED__")

    def _start_runtime(self) -> None:
        path = Path(self.model.get())
        if not path.is_file():
            messagebox.showerror("Model not found", "Train a model first, or choose a .pkl model file.")
            return
        self.state.set("Starting custom haptics…")
        self._begin("runtime", self._runtime_worker, self.game.get(), path)

    def _runtime_worker(self, game: str, path: Path) -> None:
        try:
            run_runtime(game, str(path), "dualsense", stop_event=self.stop_event, status_callback=self.messages.put)
        except Exception as error:
            self.messages.put(f"ERROR: {error}")
        finally:
            self.messages.put("__STOPPED__")

    def _stop(self) -> None:
        if self.stop_event is not None:
            self.stop_event.set()
            self.state.set("Stopping safely…")

    def _poll_messages(self) -> None:
        try:
            while True:
                message = self.messages.get_nowait()
                if message == "__STOPPED__":
                    self.record_button.configure(state="normal")
                    self.train_button.configure(state="normal")
                    self.runtime_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.task.set("idle")
                    if not self.state.get().startswith("ERROR"):
                        self.state.set("Ready.")
                    continue
                self.state.set(message)
                self.log.configure(state="normal")
                self.log.insert("end", message + "\n")
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_messages)

    def _close(self) -> None:
        self._stop()
        self._wait_for_worker_then_close()

    def _wait_for_worker_then_close(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            self.root.after(100, self._wait_for_worker_then_close)
        else:
            self.root.destroy()


def main() -> None:
    # A double-clicked Windows app may otherwise inherit an arbitrary working
    # directory. Keep recordings, trained models and reports beside the app.
    os.chdir(ROOT)
    root = tk.Tk()
    HapticsDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
