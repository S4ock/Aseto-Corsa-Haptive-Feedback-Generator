"""Minimal Windows desktop launcher for telemetry-driven haptics."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.main_runtime import run_runtime
from src.utils.config_loader import ROOT
from src.utils.safety import OFFLINE_WARNING


class HapticsDesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TelemetryDualSenseAI")
        self.root.resizable(False, False)
        self.messages: queue.Queue[str] = queue.Queue()
        self.stop_event: threading.Event | None = None
        self.worker: threading.Thread | None = None
        self.game = tk.StringVar(value="assetto_corsa")
        self.model = tk.StringVar(value=str(ROOT / "models" / "best_model.pkl"))
        self.state = tk.StringVar(value="Ready. Start an offline driving session, then press Start.")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._poll_messages()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="TelemetryDualSenseAI", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Custom USB DualSense vibration from read-only game telemetry.").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))
        warning = ttk.Label(frame, text=OFFLINE_WARNING, foreground="#9c1c1c", wraplength=480)
        warning.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 14))
        ttk.Label(frame, text="Game").grid(row=3, column=0, sticky="w")
        game_box = ttk.Combobox(frame, textvariable=self.game, values=("assetto_corsa", "f1_25"), state="readonly", width=28)
        game_box.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(10, 0))
        ttk.Label(frame, text="Trained model").grid(row=4, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.model, width=46).grid(row=4, column=1, sticky="ew", padx=(10, 8), pady=(10, 0))
        ttk.Button(frame, text="Browse…", command=self._browse).grid(row=4, column=2, pady=(10, 0))
        self.start_button = ttk.Button(frame, text="Start haptics", command=self._start)
        self.start_button.grid(row=5, column=1, sticky="ew", pady=(18, 0))
        self.stop_button = ttk.Button(frame, text="Stop", command=self._stop, state="disabled")
        self.stop_button.grid(row=5, column=2, sticky="ew", pady=(18, 0))
        ttk.Label(frame, textvariable=self.state, wraplength=480).grid(row=6, column=0, columnspan=3, sticky="w", pady=(16, 6))
        self.log = tk.Text(frame, width=70, height=9, state="disabled", wrap="word")
        self.log.grid(row=7, column=0, columnspan=3, sticky="ew")
        ttk.Label(frame, text="Start the game in offline mode first. This app outputs haptics only; it never sends driving inputs.", foreground="#555555", wraplength=480).grid(row=8, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _browse(self) -> None:
        filename = filedialog.askopenfilename(title="Choose trained model", initialdir=ROOT / "models", filetypes=[("Joblib model", "*.pkl")])
        if filename:
            self.model.set(filename)

    def _start(self) -> None:
        path = Path(self.model.get())
        if not path.is_file():
            messagebox.showerror("Model not found", "Train a model first, or choose models\\best_model.pkl.")
            return
        self.stop_event = threading.Event()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.state.set("Starting haptics runtime…")
        self.worker = threading.Thread(target=self._run_worker, args=(path, self.game.get()), name="haptics-runtime", daemon=True)
        self.worker.start()

    def _run_worker(self, path: Path, game: str) -> None:
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
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.state.set("Stopped.")
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
    root = tk.Tk()
    HapticsDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
