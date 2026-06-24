"""Downloadable desktop workspace for recording, training, and live haptics."""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.app.runtime_engine import RuntimeEngine
from src.haptics.dualsense_output import create_output
from src.haptics.mixer import RuntimeHapticMixer
from src.main_recorder import record_session
from src.main_runtime import run_runtime
from src.training.dataset_builder import load_processed_sessions
from src.training.model_io import load_artifacts
from src.training.train_models import train
from src.utils.config_loader import RESOURCE_ROOT, ROOT, load_yaml
from src.utils.safety import OFFLINE_WARNING
from src.utils.session_names import next_session_name


class HapticsDesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TelemetryDualSenseAI")
        self.root.resizable(False, False)
        self.root.configure(background="#101827")
        self._configure_style()
        self.messages: queue.Queue[str] = queue.Queue()
        self.record_stop_event: threading.Event | None = None
        self.runtime_stop_event: threading.Event | None = None
        self.record_worker: threading.Thread | None = None
        self.runtime_worker: threading.Thread | None = None
        self.training_worker: threading.Thread | None = None
        self._record_haptics = None
        self._haptics_lock = threading.Lock()
        self.game = tk.StringVar(value="assetto_corsa")
        self.session = tk.StringVar(value=next_session_name("session_001"))
        default_model = RESOURCE_ROOT / "models" / "best_model.pkl"
        self.model = tk.StringVar(value=str(default_model if default_model.exists() else ROOT / "models" / "best_model.pkl"))
        self.state = tk.StringVar(value="Ready. Start an offline driving session, then choose an action.")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._poll_messages()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=22, style="App.TFrame")
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="TelemetryDualSenseAI", style="Title.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(frame, text="Offline telemetry research • custom motors and adaptive triggers", style="Subtitle.TLabel").grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 0))
        ttk.Label(frame, text=OFFLINE_WARNING, style="Warning.TLabel", wraplength=650).grid(row=2, column=0, columnspan=4, sticky="ew", pady=(14, 16), ipadx=10, ipady=8)
        ttk.Label(frame, text="Game").grid(row=3, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=self.game, values=("assetto_corsa", "f1_25", "beamng_drive", "live_for_speed"), state="readonly", width=38).grid(row=3, column=1, columnspan=3, sticky="ew", padx=(10, 0))
        ttk.Label(frame, text="Session name").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.session, width=44).grid(row=4, column=1, columnspan=3, sticky="ew", padx=(10, 0), pady=(8, 0))
        ttk.Label(frame, text="Trained model").grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.model, width=48).grid(row=5, column=1, columnspan=2, sticky="ew", padx=(10, 8), pady=(8, 0))
        ttk.Button(frame, text="Browse...", command=self._browse).grid(row=5, column=3, pady=(8, 0))
        self.record_button = ttk.Button(frame, text="Start recording", command=self._start_recording)
        self.record_button.grid(row=6, column=0, sticky="ew", pady=(18, 0))
        self.stop_record_button = ttk.Button(frame, text="Stop recording", command=self._stop_recording, state="disabled")
        self.stop_record_button.grid(row=6, column=1, sticky="ew", padx=(8, 0), pady=(18, 0))
        self.runtime_button = ttk.Button(frame, text="Start haptics", command=self._start_runtime)
        self.runtime_button.grid(row=6, column=2, sticky="ew", padx=8, pady=(18, 0))
        self.stop_runtime_button = ttk.Button(frame, text="Stop haptics", command=self._stop_runtime, state="disabled")
        self.stop_runtime_button.grid(row=6, column=3, sticky="ew", pady=(18, 0))
        self.train_button = ttk.Button(frame, text="Train model", command=self._start_training)
        self.train_button.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        ttk.Label(frame, textvariable=self.state, wraplength=600).grid(row=8, column=0, columnspan=4, sticky="w", pady=(14, 6))
        self.log = tk.Text(frame, width=84, height=10, state="disabled", wrap="word", background="#0b1220", foreground="#d1d5db", insertbackground="#ffffff", relief="flat", padx=10, pady=8)
        self.log.grid(row=9, column=0, columnspan=4, sticky="ew")
        ttk.Label(frame, text="Recording and haptics may run together. Stop each independently. Training requires both to be stopped. This app never sends gameplay inputs.", foreground="#555555", wraplength=600).grid(row=10, column=0, columnspan=4, sticky="w", pady=(8, 0))

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background="#101827")
        style.configure("TLabel", background="#101827", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#101827", foreground="#f8fafc", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background="#101827", foreground="#94a3b8", font=("Segoe UI", 10))
        style.configure("Warning.TLabel", background="#3f1d23", foreground="#fecaca", font=("Segoe UI", 9))
        style.configure("TButton", background="#2563eb", foreground="#ffffff", padding=(10, 7), font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", "#3b82f6"), ("disabled", "#334155")], foreground=[("disabled", "#94a3b8")])
        style.configure("TEntry", fieldbackground="#f8fafc", foreground="#111827", padding=5)
        style.configure("TCombobox", fieldbackground="#f8fafc", foreground="#111827", padding=4)

    def _browse(self) -> None:
        filename = filedialog.askopenfilename(title="Choose trained model", initialdir=ROOT / "models", filetypes=[("Model", "*.pkl")])
        if filename:
            self.model.set(filename)

    @staticmethod
    def _running(worker: threading.Thread | None) -> bool:
        return worker is not None and worker.is_alive()

    def _refresh_controls(self) -> None:
        recording = self._running(self.record_worker)
        runtime = self._running(self.runtime_worker)
        training = self._running(self.training_worker)
        self.record_button.configure(state="disabled" if recording or training else "normal")
        self.stop_record_button.configure(state="normal" if recording else "disabled")
        self.runtime_button.configure(state="disabled" if runtime or training else "normal")
        self.stop_runtime_button.configure(state="normal" if runtime else "disabled")
        self.train_button.configure(state="disabled" if recording or runtime or training else "normal")

    def _start_recording(self) -> None:
        if self._running(self.training_worker):
            return
        if self._running(self.runtime_worker):
            messagebox.showerror("Start recording first", "Stop haptics, start recording, then start haptics again. This lets F1 use one shared official UDP telemetry receiver.")
            return
        name = self.session.get().strip()
        if not name:
            messagebox.showerror("Session name required", "Enter a unique session name first.")
            return
        self.state.set("Recording telemetry...")
        self.record_stop_event = threading.Event()
        self.record_worker = threading.Thread(target=self._record_worker, args=(self.game.get(), name, self.record_stop_event), name="desktop-recording", daemon=True)
        self.record_worker.start()
        self._refresh_controls()

    def _record_worker(self, game: str, session: str, stop_event: threading.Event) -> None:
        try:
            _, processed = record_session(game, session, stop_event=stop_event, on_telemetry=self._process_record_haptics)
            self.messages.put(f"Saved recording: {processed}")
            self.messages.put(f"__NEXT_SESSION__:{next_session_name(session)}")
        except Exception as error:
            self.messages.put(f"ERROR: {error}")
        finally:
            # Attached haptics must not keep the last effect active after its
            # single shared telemetry source has stopped.
            if self.runtime_stop_event is not None:
                self.runtime_stop_event.set()
            self.messages.put("__STOPPED__:recording")

    def _start_training(self) -> None:
        if self._running(self.record_worker) or self._running(self.runtime_worker):
            messagebox.showerror("Stop active tasks", "Stop recording and haptics before training so the dataset is stable.")
            return
        self.state.set("Training models... this can take a while on larger datasets.")
        self.training_worker = threading.Thread(target=self._train_worker, name="desktop-training", daemon=True)
        self.training_worker.start()
        self._refresh_controls()

    def _train_worker(self) -> None:
        try:
            config = load_yaml("training.yaml")
            metrics = train(load_processed_sessions(), config)
            self.messages.put(f"Training complete. Best model: {metrics['best_model']}; MAE: {metrics['mae']:.4f}")
        except Exception as error:
            self.messages.put(f"ERROR: {error}")
        finally:
            self.messages.put("__STOPPED__:training")

    def _start_runtime(self) -> None:
        if self._running(self.training_worker):
            return
        path = Path(self.model.get())
        if not path.is_file():
            messagebox.showerror("Model not found", "Train a model first, or choose a .pkl model file.")
            return
        self.state.set("Starting custom haptics...")
        self.runtime_stop_event = threading.Event()
        if self._running(self.record_worker):
            self.runtime_worker = threading.Thread(target=self._attached_haptics_worker, args=(path, self.runtime_stop_event), name="desktop-recording-haptics", daemon=True)
        else:
            self.runtime_worker = threading.Thread(target=self._runtime_worker, args=(self.game.get(), path, self.runtime_stop_event), name="desktop-haptics", daemon=True)
        self.runtime_worker.start()
        self._refresh_controls()

    def _runtime_worker(self, game: str, path: Path, stop_event: threading.Event) -> None:
        try:
            run_runtime(game, str(path), "dualsense", stop_event=stop_event, status_callback=lambda message: self.messages.put(f"[haptics] {message}"))
        except Exception as error:
            self.messages.put(f"ERROR: {error}")
        finally:
            self.messages.put("__STOPPED__:haptics")

    def _attached_haptics_worker(self, path: Path, stop_event: threading.Event) -> None:
        """Attach haptics to the recorder's telemetry callback (important for F1 UDP)."""
        output = None
        try:
            model, preprocessor = load_artifacts(path)
            haptics_config = load_yaml("haptics.yaml")
            games_config = load_yaml("games.yaml")
            output = create_output("dualsense", games_config.get("dualsense", {}))
            output.connect()
            processor = (RuntimeEngine(model, preprocessor, haptics_config.get("smoothing_factor", .35)), RuntimeHapticMixer(haptics_config), output)
            with self._haptics_lock:
                self._record_haptics = processor
            self.messages.put("Haptics attached to the recording telemetry stream.")
            stop_event.wait()
        except Exception as error:
            self.messages.put(f"ERROR: {error}")
        finally:
            with self._haptics_lock:
                self._record_haptics = None
            if output is not None:
                try:
                    output.stop()
                    output.close()
                except Exception:
                    pass
            self.messages.put("__STOPPED__:haptics")

    def _process_record_haptics(self, telemetry: dict) -> None:
        """Run one haptic inference from the recorder's already-normalized packet."""
        with self._haptics_lock:
            if self._record_haptics is None:
                return
            engine, mixer, output = self._record_haptics
            feedback, _ = engine.predict(telemetry)
            output.send_feedback(mixer.apply(telemetry, feedback))

    def _stop_recording(self) -> None:
        if self.record_stop_event is not None:
            self.record_stop_event.set()
            self.state.set("Stopping recording safely...")

    def _stop_runtime(self) -> None:
        if self.runtime_stop_event is not None:
            self.runtime_stop_event.set()
            self.state.set("Stopping haptics safely...")

    def _poll_messages(self) -> None:
        try:
            while True:
                message = self.messages.get_nowait()
                if message.startswith("__STOPPED__:"):
                    self._refresh_controls()
                    if not self.state.get().startswith("ERROR"):
                        self.state.set("Ready.")
                    continue
                if message.startswith("__NEXT_SESSION__:"):
                    self.session.set(message.split(":", 1)[1])
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
        self._stop_recording()
        self._stop_runtime()
        self._wait_for_workers_then_close()

    def _wait_for_workers_then_close(self) -> None:
        if any(self._running(worker) for worker in (self.record_worker, self.runtime_worker, self.training_worker)):
            self.root.after(100, self._wait_for_workers_then_close)
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
