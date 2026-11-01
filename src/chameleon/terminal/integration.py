import base64
import os
import secrets
from pathlib import Path

from chameleon.core.schemas import ShellName
from chameleon.platform.windows.shells import ps_quote
from chameleon.platform.windows.system import shell_executable


def child_shell(shell: ShellName, state_file: Path) -> tuple[list[str], dict[str, str], str]:
    token = secrets.token_hex(16)
    env = dict(os.environ)
    env["CHAMELEON_PROMPT_TOKEN"] = token
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    executable = shell_executable(shell)
    if shell == "cmd":
        # OSC title is supported through ConPTY, unlike arbitrary unsupported OSCs.
        # It is consumed locally, and emitted after the visible shell prompt.
        env["PROMPT"] = f"$P$G$E]0;Chameleon-{token};$P$E\\"
        return [executable, "/d", "/q", "/v:off"], env, token
    script = f"""
Import-Module PSReadLine -ErrorAction SilentlyContinue
if (Get-Command Set-PSReadLineOption -ErrorAction SilentlyContinue) {{
    Set-PSReadLineOption -HistorySaveStyle SaveNothing
    if ((Get-Command Set-PSReadLineOption).Parameters.ContainsKey('PredictionSource')) {{ Set-PSReadLineOption -PredictionSource None }}
}}
$global:ChameleonStatePath = {ps_quote(str(state_file))}
function global:prompt {{
    $state = @{{ cwd = (Get-Location).Path; aliases = @((Get-Alias).Name) + @((Get-Command -ListImported -CommandType Function,Cmdlet).Name); shell_version = $PSVersionTable.PSVersion.ToString() }}
    [IO.File]::WriteAllText($global:ChameleonStatePath, ($state | ConvertTo-Json -Compress), (New-Object Text.UTF8Encoding($false)))
    'PS ' + (Get-Location).Path + '> ' + [char]27 + ']0;Chameleon-{token};' + (Get-Location).Path + [char]7
}}
"""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    # No ExecutionPolicy change: a command passed to the child shell is not a profile.
    return [executable, "-NoLogo", "-NoExit", "-EncodedCommand", encoded], env, token
