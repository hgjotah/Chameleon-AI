"""Bounded native syntax discovery. Generated commands are parsed, never run."""

import base64
import json
import os
import re
import subprocess
from functools import lru_cache

from chameleon.core.context import Context
from chameleon.platform.windows.system import hidden_run, shell_executable


def command_heads(command: str) -> list[str]:
    """Find CMD pipeline heads without splitting quoted literal strings."""
    pieces = re.split(r'("[^"]*"|\^[\s\S])', command)
    visible = "".join(" " * len(p) if i % 2 else p for i, p in enumerate(pieces))
    starts = [0] + [match.end() for match in re.finditer(r"&&|\|\||[&|]", visible)]
    result = []
    for start in starts:
        match = re.match(r'\s*@?(?:"([^"]+)"|([^\s&|<>]+))', command[start:])
        if match:
            result.append(match[1] or match[2])
    return result[:12]


@lru_cache(maxsize=64)
def cmd_reference(name: str) -> str:
    from chameleon.core.intents import CMD_BUILTINS

    name = name.partition("=")[0]

    if os.name != "nt" or name.casefold() not in CMD_BUILTINS | {
        entry[0].casefold() for entry in cmd_catalog()
    }:
        return ""
    try:
        result = hidden_run([shell_executable("cmd"), "/d", "/c", "help", name], timeout=3)
        # Native help is localized OEM text. It contains syntax, not file content.
        return (result.stdout or result.stderr).strip()[:6500]
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return ""


@lru_cache(maxsize=1)
def cmd_catalog() -> list[tuple[str, str]]:
    if os.name != "nt":
        return []
    try:
        result = hidden_run([shell_executable("cmd"), "/d", "/c", "help"], timeout=3)
        return [
            (m[1], m[2])
            for line in result.stdout.splitlines()
            if (m := re.match(r"^([A-Z][A-Z0-9]+)\s{2,}(.+)", line))
        ]
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return []


def powershell_reference(command: str, context: Context) -> dict:
    if os.name != "nt":
        return {"errors": [], "reference": ""}
    encoded = base64.b64encode(command.encode("utf-8")).decode("ascii")
    # The model string is decoded into ParseInput's DATA argument. Never pass it
    # to ScriptBlock.Create/Invoke-Expression or -Command for execution.
    script = r"""
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__DATA__'))
$tokens=$null; $parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$parseErrors)
$problems=@($parseErrors | ForEach-Object {$_.Message})
$refs=@(); $heads=@()
if($ast.EndBlock.Statements.Count -eq 1 -and $ast.EndBlock.Statements[0] -is [Management.Automation.Language.PipelineAst]) {
    $elements=$ast.EndBlock.Statements[0].PipelineElements
    if($elements.Count -eq 1 -and $elements[0] -is [Management.Automation.Language.CommandExpressionAst] -and $elements[0].Expression -is [Management.Automation.Language.StringConstantExpressionAst]) {
        $problems+='A bare string/path is not a command that queries the system.'
    }
}
if($text -match '\$Host\.UI\.RawUI\.') {
    foreach($property in $Host.UI.RawUI.PSObject.Properties) {
        $value=$property.Value
        $refs+= ('$Host.UI.RawUI.'+$property.Name+' : '+$property.TypeNameOfValue)
        if($null -ne $value -and $value.GetType().IsEnum) {
            $refs+= ('Valid values: '+([Enum]::GetNames($value.GetType()) -join ', '))
        }
    }
    foreach($assignment in $ast.FindAll({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst]},$true)) {
        if($assignment.Left.Extent.Text -notmatch '^\$Host\.UI\.RawUI\.([A-Za-z]+)$') {continue}
        $member=$Matches[1]
        $property=$Host.UI.RawUI.PSObject.Properties[$member]
        if(-not $property) {$problems+='Unknown session property: '+$member; continue}
        $type=$property.Value.GetType()
        $literal=$assignment.Right.Extent.Text.Trim()
        if($type.IsEnum -and $literal -match '^(?:\[(?:System\.)?ConsoleColor\]::)?["'']?([A-Za-z]+)["'']?$') {
            try {[void][Enum]::Parse($type,$Matches[1],$true)} catch {$problems+='Invalid '+$type.Name+' value for '+$member}
        }
    }
}
foreach($node in @($ast.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst]},$true)) | Select-Object -First 12) {
    $name=$node.GetCommandName()
    if(-not $name) {continue}
    $heads+= $name
    # Paths/scripts are checked as paths by the app; don't import arbitrary files.
    if($name -notmatch '^[A-Za-z][A-Za-z0-9_.-]*$') {
        $candidate=$name
        if(-not [IO.Path]::IsPathRooted($candidate)) {$candidate=Join-Path '__CWD__' $candidate}
        if(-not [IO.File]::Exists($candidate)) {$problems+='Executable/script file does not exist: '+$name}
        continue
    }
    $info=Get-Command -Name $name -ErrorAction SilentlyContinue | Select-Object -First 1
    if(-not $info) {$problems+= 'Command not available: '+$name; continue}
    if($info.CommandType -eq 'Alias') {$info=$info.ResolvedCommand}
    if($info.CommandType -in @('Cmdlet','Function','Filter')) {
        $refs+= ($info.Name+' '+(($info.ParameterSets | Select-Object -First 3 | ForEach-Object {$_.ToString()}) -join ' | '))
        $binding=[Management.Automation.Language.StaticParameterBinder]::BindCommand($node,$true)
        foreach($errorInfo in $binding.BindingExceptions.Values) {$problems+=$errorInfo.BindingException.Message}
        foreach($part in $node.CommandElements) {
            if($part -isnot [Management.Automation.Language.CommandParameterAst]) {continue}
            $parameter=$part.ParameterName
            $matches=@($info.Parameters.Keys | Where-Object {$_ -like ($parameter+'*')})
            if(-not $matches.Count) {
                $matches=@($info.Parameters.Values | Where-Object {$_.Aliases -contains $parameter})
            }
            if(-not $matches.Count) {$problems+= 'Unknown parameter for '+$info.Name+': -'+$parameter}
        }
    }
}
@{errors=@($problems | Select-Object -First 6); heads=$heads; reference=($refs -join "`n")} | ConvertTo-Json -Depth 4 -Compress
""".replace("__DATA__", encoded).replace("__CWD__", context.cwd.replace("'", "''"))
    data = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        result = hidden_run(
            [
                context.shell_executable or shell_executable(context.shell),
                "-NoLogo",
                "-NoProfile",
                "-EncodedCommand",
                data,
            ],
            timeout=6,
            encoding="utf-8",
        )
        if result.returncode:
            return {
                "errors": ["Native syntax inspection failed; no command executed."],
                "reference": "",
            }
        parsed = json.loads(result.stdout)
        # Parent-only aliases/functions cannot be rediscovered in a fresh shell.
        parsed["errors"] = [
            message
            for message in parsed.get("errors", [])
            if not (
                message.startswith("Command not available: ")
                and message.split(": ", 1)[1].casefold() in context.executables
            )
        ]
        parsed["reference"] = str(parsed.get("reference", ""))[:6500]
        return parsed
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {
            "errors": ["Native syntax inspection unavailable; no command executed."],
            "reference": "",
        }


def cmd_argument_errors(command: str, reference: str) -> list[str]:
    """Apply a value constraint declared by installed help, not a task/answer table."""
    if not reference or len(command_heads(command)) != 1:
        return []
    name = command.strip().split()[0].partition("=")[0]
    simple_usage = re.search(r"^\s*" + re.escape(name) + r"\s+\[\w+\]\s*$", reference, re.M | re.I)
    hex_pair = re.search(r"\b(?:two|dos|2)\b[^\r\n]{0,40}hexadec", reference, re.I)
    if simple_usage and hex_pair:
        argument = command.strip()[len(name) :].lstrip(" =\t")
        if argument and not re.fullmatch(r"[0-9a-fA-F]{1,2}", argument):
            return [
                "Installed native help requires a one/two-digit hexadecimal attribute; this argument is invalid."
            ]
    return []
