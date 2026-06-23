param([switch]$OneFile)

$ErrorActionPreference = 'Stop'
python -m pip install pyinstaller

$arguments = @('--noconfirm', '--clean', '--windowed', '--name', 'TelemetryDualSenseAI', '--paths', '.', '--add-data', 'config;config', '--add-data', 'data;data')
# Deep-learning/CUDA training is intentionally not part of this project.
$arguments += @('--exclude-module', 'torch', '--exclude-module', 'torchvision', '--exclude-module', 'triton')
if (Test-Path -LiteralPath 'models\best_model.pkl') { $arguments += @('--add-data', 'models\best_model.pkl;models') }
if (Test-Path -LiteralPath 'models\preprocessor.pkl') { $arguments += @('--add-data', 'models\preprocessor.pkl;models') }
if (Test-Path -LiteralPath 'hidapi.dll') { $arguments += @('--add-binary', 'hidapi.dll;.') }
if ($OneFile) { $arguments += '--onefile' }
$arguments += 'src\main_desktop_app.py'
python -m PyInstaller @arguments

Write-Host "Build complete. Share the contents of dist\TelemetryDualSenseAI (or the single EXE when -OneFile is used)."
