$ErrorActionPreference = 'Stop'
$chameleonWorkspace = (Resolve-Path (Split-Path $PSScriptRoot -Parent)).Path
foreach ($chameleonName in @('build','dist','.pytest_cache','.mypy_cache','.ruff_cache')) {
    $chameleonTarget = [IO.Path]::GetFullPath((Join-Path $chameleonWorkspace $chameleonName))
    if (-not $chameleonTarget.StartsWith($chameleonWorkspace + [IO.Path]::DirectorySeparatorChar)) { throw 'Unsafe cleanup target' }
    if (Test-Path -LiteralPath $chameleonTarget) { Remove-Item -LiteralPath $chameleonTarget -Recurse -Force }
}
