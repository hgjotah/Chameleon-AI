import os

import pytest

from chameleon.platform.windows.system import child_environment, hidden_run, shell_executable


@pytest.mark.windows
def test_windows_powershell_modules_survive_pwsh_parent() -> None:
    result = hidden_run([shell_executable("powershell"), "-NoProfile", "-Command", "Get-ExecutionPolicy; Get-Acl $env:TEMP | Select-Object -ExpandProperty Owner"])
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() and not result.stderr.strip()


def test_environment_is_not_mutated() -> None:
    original = {'PATH': os.environ['PATH'], 'PSModulePath': 'edition-specific', 'CUSTOM': 'keep'}
    result = child_environment(original, 'powershell.exe')
    assert 'PSModulePath' not in result and result['CUSTOM'] == 'keep'
    assert original['PSModulePath'] == 'edition-specific'
    assert child_environment(original, 'cmd.exe')['PSModulePath'] == 'edition-specific'
