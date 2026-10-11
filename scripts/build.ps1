param([switch]$SkipInstall, [switch]$SkipTests)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3.13 -m venv .venv
    if ($LASTEXITCODE) { throw 'Python 3.13 x64 is required for source builds.' }
}
$chameleonPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not $SkipInstall) {
    & $chameleonPython -m pip install -r requirements.lock
    if ($LASTEXITCODE) { throw 'Dependency installation failed' }
    & $chameleonPython -m pip install -e . --no-deps
    if ($LASTEXITCODE) { throw 'Project installation failed' }
    npm.cmd ci --ignore-scripts
    if ($LASTEXITCODE) { throw 'npm assets failed' }
    & $chameleonPython scripts/vendor_assets.py
}
& $chameleonPython scripts/make_icon.py
& $chameleonPython scripts/collect_licenses.py
if (-not $SkipTests) {
    & $chameleonPython -m ruff check src tests scripts installer/entry.py installer/bootstrap.py
    if ($LASTEXITCODE) { throw 'Lint failed' }
    & $chameleonPython -m mypy src
    if ($LASTEXITCODE) { throw 'Type checking failed' }
    & $chameleonPython -m pytest -m 'not ollama'
    if ($LASTEXITCODE) { throw 'Tests failed' }
}
& $chameleonPython -m PyInstaller --noconfirm --clean installer/chameleon.spec
if ($LASTEXITCODE) { throw 'Application build failed' }
& $chameleonPython scripts/verify_frozen.py
if ($LASTEXITCODE) { throw 'Bundled source verification failed' }
& $chameleonPython scripts/package_release.py
if ($LASTEXITCODE) { throw 'Payload packaging failed' }
$chameleonIcon = Join-Path (Get-Location) 'src/chameleon/assets/icons/chameleon.ico'
$chameleonLogo = Join-Path (Get-Location) 'src/chameleon/assets/icons/chameleon.png'
$chameleonPayload = Join-Path (Get-Location) 'build/payload.zip'
$chameleonBootstrap = Join-Path (Get-Location) 'installer/bootstrap.py'
& $chameleonPython -m PyInstaller --noconfirm --clean --onefile --windowed --name ChameleonSetup --icon $chameleonIcon --add-data "$chameleonPayload;." --add-data "$chameleonLogo;." --distpath dist --workpath build/bootstrap --specpath build/bootstrap $chameleonBootstrap
if ($LASTEXITCODE) { throw 'Setup build failed' }
& $chameleonPython scripts/verify_frozen.py --installer
if ($LASTEXITCODE) { throw 'Installer payload verification failed' }
& $chameleonPython scripts/frozen_smoke.py
if ($LASTEXITCODE) { throw 'Executable/renderer/installer smoke failed' }
& $chameleonPython scripts/package_release.py --final
if ($LASTEXITCODE) { throw 'Release packaging failed' }
Write-Host 'Build complete: dist/ChameleonSetup.exe and dist/Chameleon/'
