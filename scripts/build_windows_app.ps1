param(
    [switch]$OneFile,
    [switch]$IncludeCuda
)

$ErrorActionPreference = 'Stop'
python -m pip install pyinstaller

$arguments = @('--noconfirm', '--clean', '--windowed', '--name', 'TelemetryDualSenseAI', '--paths', '.', '--add-data', 'config;config', '--add-data', 'data;data')
if (-not $IncludeCuda) {
    # Standard GitHub download: smaller CPU app. CUDA training stays available from source.
    $arguments += @('--exclude-module', 'torch', '--exclude-module', 'torchvision', '--exclude-module', 'triton')
}
if (Test-Path -LiteralPath 'models\best_model.pkl') { $arguments += @('--add-data', 'models\best_model.pkl;models') }
if (Test-Path -LiteralPath 'hidapi.dll') { $arguments += @('--add-binary', 'hidapi.dll;.') }
if ($OneFile) { $arguments += '--onefile' }
$arguments += 'src\main_desktop_app.py'
python -m PyInstaller @arguments

Write-Host "Build complete. Share the contents of dist\TelemetryDualSenseAI (or the single EXE when -OneFile is used). Use -IncludeCuda only for a much larger CUDA build."
