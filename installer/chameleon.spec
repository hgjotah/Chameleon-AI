# Shared Python/Qt runtime for three entry points; no Python required on target.
from pathlib import Path
import os
import sys
from importlib.util import find_spec
# Dependency scanning must not pick unrelated ICU/API shim DLLs from developer
# tools on PATH (for example Poppler). Qt uses the native Windows ICU ABI.
windows = Path(os.environ['SystemRoot'])
os.environ['PATH'] = os.pathsep.join([str(windows / 'System32'), str(windows), str(Path(sys.executable).parent)])
root = Path(SPECPATH).parent
assets = root / 'src' / 'chameleon' / 'assets'
winpty_root = Path(find_spec('winpty').origin).parent
# The side-by-side ConPTY DLL launches this executable dynamically; DLL scanning
# cannot discover it. Without it, the native shell immediately loses its PTY.
a = Analysis([str(root / 'installer' / 'entry.py')], pathex=[str(root / 'src')], binaries=[(str(winpty_root / 'OpenConsole.exe'), 'winpty')], datas=[(str(assets), 'chameleon/assets')], hiddenimports=['chameleon.cli','chameleon.terminal.app','chameleon.terminal.window','chameleon.setup.app','chameleon.setup.settings','winpty'], excludes=['tkinter','pytest','mypy','ruff','PIL'], noarchive=False)
pyz = PYZ(a.pure)
core = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ChameleonCore', console=True, icon=str(assets / 'icons' / 'chameleon.ico'))
terminal = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ChameleonTerminal', console=False, icon=str(assets / 'icons' / 'chameleon.ico'))
setup = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ChameleonSetup', console=False, icon=str(assets / 'icons' / 'chameleon.ico'))
coll = COLLECT(core, terminal, setup, a.binaries, a.datas, strip=False, upx=False, name='Chameleon')
