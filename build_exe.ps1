# build.ps1 – PowerShell script to build main.exe for UMAMSME-Stat-Calc
# Run from your project root with venv activated

# 1. Ensure venv is activated
if (-not (Test-Path .\venv\Scripts\Activate.ps1)) {
    Write-Host "Virtual environment not found. Please create and activate venv first."
    exit 1
}

# 2. Install PyInstaller if needed
pip show pyinstaller > $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..."
    pip install pyinstaller
}

# 3. Clean previous build artifacts
Remove-Item -Recurse -Force dist, build, main.spec -ErrorAction SilentlyContinue

# 4. Build via package entry-point
pyinstaller --name main --noconfirm --onedir --windowed `
  --add-data "stat_planner/assets;stat_planner/assets" `
  stat_planner/__main__.py

Write-Host "Build complete! Your executable lives in 'dist\main\main.exe'."