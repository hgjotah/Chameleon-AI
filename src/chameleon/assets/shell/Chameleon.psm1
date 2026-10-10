function global:chameleon {
    [CmdletBinding(PositionalBinding=$false)]
    param([Parameter(ValueFromRemainingArguments=$true)][string[]] $Request)
    $core = Join-Path $PSScriptRoot '..\core\ChameleonCore.exe'
    $oldEncoding = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $json = & $core --emit powershell --session $PID --cwd (Get-Location).Path @Request
        if ($LASTEXITCODE -ne 0 -or -not $json) { return }
        $plan = ($json -join "`n") | ConvertFrom-Json
        if ($plan.version -ne 1 -or $plan.intent -ne 'execute') { throw 'Invalid Chameleon protocol' }
        foreach ($action in $plan.actions) {
            switch ($action.kind) {
                { $_ -in 'create','mkdir','copy','move' } {
                    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($action | ConvertTo-Json -Compress)))
                    & $core apply --encoded $encoded
                    if ($LASTEXITCODE -ne 0) { throw 'No se pudo completar la acción de archivo; las acciones siguientes se cancelaron.' }
                }
                'cd' { Set-Location -LiteralPath $action.path -ErrorAction Stop }
                'clear' { Clear-Host }
                { $_ -in 'list','find' } {
                    if ($action.min_size_bytes -gt 0 -or $action.modified_after -or $action.file_type -ne 'any') {
                        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($action | ConvertTo-Json -Compress)))
                        & $core query --encoded $encoded
                        if ($LASTEXITCODE -ne 0) { throw 'Consulta fallida' }
                    } else {
                        Get-ChildItem -LiteralPath $action.path -Filter $action.pattern -Recurse:($action.recursive -or $action.kind -eq 'find') -ErrorAction Stop
                    }
                }
                'processes' {
                    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($action | ConvertTo-Json -Compress)))
                    & $core query --encoded $encoded
                }
                'read' { Get-Content -LiteralPath $action.path -Encoding UTF8 -ErrorAction Stop }
                'delete' { Remove-Item -LiteralPath $action.path -Recurse:$action.recursive -ErrorAction Stop }
                'env' { [Environment]::SetEnvironmentVariable($action.name, $action.value, 'Process') }
                'command' { & ([ScriptBlock]::Create($action.command)) }
                default { throw 'Unknown Chameleon action' }
            }
        }
    } catch {
        Write-Error ('Chameleon: ' + $_.Exception.Message)
    } finally {
        [Console]::OutputEncoding = $oldEncoding
    }
}
Export-ModuleMember -Function chameleon
