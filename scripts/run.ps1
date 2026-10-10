param([ValidateSet('terminal','setup','settings')][string]$App = 'terminal')
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($App -eq 'terminal') { & .\.venv\Scripts\python.exe -c 'from chameleon.terminal.app import main; raise SystemExit(main())' }
else { & .\.venv\Scripts\python.exe -c 'from chameleon.setup.app import main; raise SystemExit(main())' $App }
