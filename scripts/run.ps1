param([ValidateSet('terminal','setup','settings')][string]$App = 'terminal')
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($App -eq 'setup') {
    # Store Python virtualizes AppData and HKCU. Installation must run from the
    # standalone executable so native CMD/PowerShell see the same files/registry.
    if (!(Test-Path -LiteralPath '.\dist\ChameleonSetup.exe')) {
        Write-Error 'Construye primero con scripts/build.ps1 y ejecuta dist/ChameleonSetup.exe para instalar o reparar.'
        exit 1
    }
    & .\dist\ChameleonSetup.exe
    exit $LASTEXITCODE
}
if ($App -eq 'terminal') { & .\.venv\Scripts\python.exe -c 'from chameleon.terminal.app import main; raise SystemExit(main())' }
else { & .\.venv\Scripts\python.exe -c 'from chameleon.setup.app import main; raise SystemExit(main())' $App }
