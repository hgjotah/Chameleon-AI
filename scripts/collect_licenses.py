"""Collect installed wheel notices and Python/Qt license texts for distribution."""

import importlib.metadata
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "src" / "chameleon" / "assets" / "licenses"
target.mkdir(parents=True, exist_ok=True)
for distribution in importlib.metadata.distributions():
    name = distribution.metadata.get("Name", "unknown")
    for file in distribution.files or []:
        if ".dist-info" in str(file) and any(
            part.casefold()
            in (
                "licenses",
                "license",
                "license.txt",
                "license.md",
                "copying",
                "notice",
                "notice.txt",
            )
            for part in file.parts
        ):
            source = Path(distribution.locate_file(file))
            if source.is_file() and source.suffix not in (".py", ".pyc"):
                # Wheel bundles can contain several different LICENSE.txt files.
                # Preserve their paths so none overwrites the main/bundled notice.
                package_target = (target / name).resolve()
                destination = (package_target / Path(*file.parts)).resolve()
                if not destination.is_relative_to(package_target):
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.is_file():
    shutil.copy2(python_license, target / "PYTHON-LICENSE.txt")
shutil.copy2(root / "THIRD_PARTY_NOTICES.md", target / "THIRD_PARTY_NOTICES.md")
