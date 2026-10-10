"""Copy pinned, audited npm resources into the offline renderer."""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "src" / "chameleon" / "assets" / "web" / "vendor"
DEST.mkdir(parents=True, exist_ok=True)
for source, target in [
    ("@xterm/xterm/lib/xterm.js", "xterm.js"),
    ("@xterm/xterm/css/xterm.css", "xterm.css"),
    ("@xterm/addon-fit/lib/addon-fit.js", "addon-fit.js"),
    ("@xterm/addon-web-links/lib/addon-web-links.js", "addon-web-links.js"),
    ("@xterm/xterm/LICENSE", "XTERM-LICENSE.txt"),
    ("@xterm/addon-fit/LICENSE", "FIT-LICENSE.txt"),
    ("@xterm/addon-web-links/LICENSE", "WEBLINKS-LICENSE.txt"),
]:
    shutil.copy2(ROOT / "node_modules" / source, DEST / target)
