import sys
from pathlib import Path

name = Path(sys.executable).stem.casefold()
if "terminal" in name:
    from chameleon.terminal.app import main
elif "setup" in name:
    from chameleon.setup.app import main
else:
    from chameleon.cli import main

raise SystemExit(main())
