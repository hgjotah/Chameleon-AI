param([ValidateSet('terminal','setup','settings')][string]$App = 'terminal')
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($App -eq 'setup') {
    # Store Python virtualizes AppData and HKCU. Installation must run from the
    # standalone executable so native CMD/PowerShell see the same files/registry.
    if (!(Test-Path -LiteralPath '.\dist\ChameleonSetup.exe')) {
        Write-Error 'Build with scripts/build.ps1 first, then run dist/ChameleonSetup.exe to install or repair.'
        exit 1
    }
    & .\dist\ChameleonSetup.exe
    exit $LASTEXITCODE
}
if (Test-Path -LiteralPath '.\dist\Chameleon\ChameleonCore.exe') {
    & .\dist\Chameleon\ChameleonCore.exe $App
    exit $LASTEXITCODE
}
if ($App -eq 'terminal') { & .\.venv\Scripts\python.exe -c 'from chameleon.terminal.app import main; raise SystemExit(main())' }
else { & .\.venv\Scripts\python.exe -c 'from chameleon.setup.app import main; raise SystemExit(main())' $App }
