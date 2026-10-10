# Building

Windows x64, Python 3.13 x64 and Node.js 22+. No Inno Setup, Visual Studio or Rust compiler is needed because pywinpty is pinned to a published wheel.

```powershell
.\scripts\build.ps1
```

The script creates `.venv`, installs `requirements.lock`, installs this package editable without re-resolving dependencies, runs npm ci, vendors resources and their licenses, generates the icon, runs ruff/mypy/pytest, builds the shared runtime and the standalone Setup. It checks bundled source/payload integrity and executes the frozen CLI, shell wrappers, GUI and extracted installer before packaging the final ZIPs. Artifacts are under `dist`. Keep `_internal` with all three onedir executables.

For iteration: `build.ps1 -SkipInstall`; `-SkipTests` should only be used after the checks have passed for the same source revision. `scripts/clean.ps1` checks absolute targets inside the repository before deleting only known build directories.

`scripts/run.ps1 setup` launches the built standalone installer. Do not install from a source Python process supplied by Microsoft Store: its AppData/HKCU virtualization can put files and registration in a private location invisible to native shell processes ([Python's Windows documentation](https://docs.python.org/3.13/using/windows.html#redirection-of-local-data-registry-and-temporary-paths)). Store Python can still build and test the project; the frozen installer runs independently of it.

Reproducibility fixes Python minor version, all pip packages and npm lockfile. PyInstaller timestamps/platform DLL metadata may differ, so byte-for-byte reproducibility is not claimed. `SHA256SUMS.json` identifies each produced distribution. For commercial release sign executables and installer using your certificate outside the repository. CI requires no signing secret.

Verification:

```powershell
.venv\Scripts\python -m ruff check src tests scripts installer/entry.py installer/bootstrap.py
.venv\Scripts\python -m mypy src
.venv\Scripts\python -m pytest -m 'not ollama'
.venv\Scripts\python scripts/gui_smoke.py cmd
.venv\Scripts\python scripts/gui_smoke.py powershell
.venv\Scripts\python scripts/gui_smoke.py cmd --ai
.venv\Scripts\python scripts/setup_smoke.py
.venv\Scripts\python scripts/frozen_smoke.py
$env:CHAMELEON_TEST_OLLAMA = '1'
.venv\Scripts\python -m pytest -m ollama
```

`setup_smoke.py` copies the actual payload into a temporary home, exercises the Qt worker and real Qwen probe, then removes it. It leaves the operator's PATH/profiles untouched. `frozen_smoke.py` requires the completed build and checks the bundled CLI, wrappers, GUI, installer extraction and removal. Screenshots and machine-readable evidence are written to ignored `artifacts/`.

The workflow uses immutable action SHAs verified against official release tags. See [GitHub's secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) when updating these dependencies.
