# TelemetryDualSenseAI

**Official telemetry in. Custom research haptics out.**

TelemetryDualSenseAI is an offline research prototype for accessibility and immersion. It reads supported racing-game telemetry, builds transparent custom haptic labels, trains prediction models, and sends optional left/right USB DualSense vibration during offline driving.

> **Use this only offline/single-player/time-trial. This tool does not modify gameplay inputs.**

## What it does

```text
Official game telemetry
        ↓
Normalized vehicle state + custom haptic labels
        ↓
Classical ML / CUDA deep-learning training
        ↓
Smoothed hybrid haptic mixer
        ↓
USB DualSense vibration or safe terminal stub output
```

The project predicts these normalized `0.0–1.0` targets:

- left/right trigger resistance and pulses (recorded/trained targets; physical triggers are not yet enabled)
- left/right vibration motor strength
- vibration frequency
- haptic events: `wheel_slip`, `off_track`, and `collision`

## Safety boundaries

`safe_mode: true` is mandatory. This project:

- uses only configured official UDP telemetry or documented read-only shared-memory telemetry;
- never reads/writes arbitrary game memory, scans processes, injects DLLs, hooks games, modifies game files, or bypasses anti-cheat;
- never creates a virtual controller or sends steering, throttle, brake, gear, menu, or gameplay commands;
- does not capture, decode, or learn from proprietary commercial-game haptic packets;
- is for offline research only, never online/ranked/multiplayer use.

If telemetry or hardware output is unavailable, the application fails safely or uses stub logging.

## Supported status

| Game/source | Telemetry status | Notes |
|---|---|---|
| F1 with UDP Format 2026 | Working | Reads official car telemetry plus collision events. Configure it as `f1_25` in this project. |
| Original Assetto Corsa (Windows) | Working | Reads documented `Local\acpmf_physics` telemetry, including inferred collision events from published damage values. |
| Mock mode | Working | Full no-game pipeline for development/testing. |
| Forza Horizon 5 | Receiver only | Receives configured Data Out UDP, but binary field decoding is not implemented yet. |
| Assetto Corsa Competizione | Unsupported | Uses a different telemetry interface. |

## Setup

Install Python 3.11+ and project dependencies:

```powershell
cd "C:\Users\user\OneDrive\Documents\dual sense"
python -m pip install -r requirements.txt
```

### Optional CUDA deep learning

For an NVIDIA GPU, install the CUDA PyTorch wheel and verify it:

```powershell
python -m pip install -r requirements-cuda.txt
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

The configured trainer compares Random Forest, HistGradientBoosting, sklearn MLP, CatBoost, and a PyTorch deep MLP. It saves the best validation model automatically. CUDA is required when `torch_deep_mlp` remains in `config/training.yaml`.

## Fast mock demo

Run the complete safe pipeline without a game or controller:

```powershell
python -m src.main_mock_demo
```

It creates mock recordings, trains CPU models, and runs stub output.

## Recording F1 telemetry

In F1 Telemetry Settings:

- UDP Telemetry: `On`
- UDP Broadcast Mode: `Off`
- UDP IP Address: `127.0.0.1`
- UDP Port: `20777`
- UDP Format: `2026`

Start the recorder before driving offline:

```powershell
python -m src.main_recorder --game f1_25 --session-name f1_training_001 --max-packets 100000
```

Press `Ctrl+C` once to save raw packets, processed CSV labels, and metadata safely.

## Recording original Assetto Corsa telemetry

There is no UDP toggle. Assetto Corsa creates its documented local telemetry mapping only after an offline session has loaded and the car is on track.

```powershell
python -m src.main_recorder --game assetto_corsa --session-name ac_training_001 --max-packets 100000
```

Record varied sessions: braking zones, throttle exits, high-RPM runs, kerbs/grass/gravel, wheel slip, and safe offline collisions. More rare events improve those haptic effects more than additional normal laps.

## Training

Processed recordings are resampled to a fixed 60 Hz time base before features are built. This keeps F1 and Assetto Corsa windows comparable even though their native telemetry rates differ.

```powershell
python -m src.main_train
notepad results\metrics.json
```

The default configuration combines all processed sessions and uses a random 80/20 split. This is useful for prototype feedback quality, but it is optimistic because nearby rows from one session may appear in both partitions. For strict research evaluation, set `include_all_games: false`, use `validation_strategy: group_by_session`, and reserve an unseen game/session.

Outputs:

- `models/best_model.pkl` and `models/preprocessor.pkl`
- `results/metrics.json`
- prediction/error plots and feature importance where supported
- `data/processed/training_table.csv`

## Live haptics runtime

Load into an offline driving session first, then run one of:

```powershell
python -m src.main_runtime --game f1_25 --model models\best_model.pkl --output dualsense
python -m src.main_runtime --game assetto_corsa --model models\best_model.pkl --output dualsense
```

Runtime continues until `Ctrl+C`. It uses a fixed 60 Hz inference cadence, holds the last prediction between updates, and mixes continuous RPM/road feedback with wheel-slip and collision overlays using attack/release envelopes.

Disable any in-game controller rumble when evaluating the project’s custom feedback, otherwise the game may compete for the controller’s motors.

## Desktop app and Windows download build

Windows users can download `TelemetryDualSenseAI-windows.zip` from this repository's **Releases** page, extract the whole ZIP, and double-click `TelemetryDualSenseAI.exe`. Do not run it from inside the ZIP. The app keeps new recordings, trained models, and reports next to the executable.

For a simple Start/Stop desktop interface, run:

```powershell
python -m src.main_desktop_app
```

Choose the game and model, then use **Start recording**, **Train model**, or **Start haptics** after the game has entered an offline driving session. Press **Stop current action** to safely finish recording or haptics.

To build a Windows app for distribution:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_app.ps1
```

The distributable is created under `dist\TelemetryDualSenseAI`. Use `-OneFile` to produce a single executable instead. The default build is a smaller CPU desktop app; use `-IncludeCuda` only when you deliberately need the much larger CUDA training build. A packaged release still needs the expected telemetry configuration and a trained model; direct USB haptics also requires `hidapi.dll`.

## USB DualSense vibration

`--output stub` is always safe and only prints haptic values. `--output dualsense` prefers a direct USB HID backend that sends only left/right vibration strengths—no virtual controller and no gameplay inputs.

For direct USB output on Windows:

1. Install `requirements.txt`.
2. Download the 64-bit `hidapi.dll` from the [HIDAPI releases](https://github.com/libusb/hidapi/releases).
3. Place it in the project root as `hidapi.dll`.
4. Test without a game running:

```powershell
python -m src.main_dualsense_test
```

The current portable output path enables vibration motors only. Physical adaptive-trigger effects are not yet enabled.

## Research evidence report

```powershell
python -m src.training.report_generator
```

This creates `results/research_evidence_report.md` with dataset counts, haptic event balance, model metrics, limitations, safety statement, and reproducibility notes.

## Project limitations

- Haptic labels are custom telemetry-derived research labels, not native game haptics or user-preference labels.
- Collision/off-road examples are naturally rare and need deliberate offline data collection.
- Forza binary telemetry decoding and Assetto Corsa Competizione support are not implemented.
- A high random-split score shows the model reproduces its own labels well; it does not prove cross-game generalization.
