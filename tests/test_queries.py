import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from chameleon.core.queries import file_query, process_query
from chameleon.core.schemas import Action


def test_filters_size_date_unicode(tmp_path: Path) -> None:
    fresh = tmp_path / "Niño.py"
    fresh.write_bytes(b"x" * 1048577)
    small = tmp_path / "small.py"
    small.write_bytes(b"x")
    old = tmp_path / "old.py"
    old.write_bytes(b"x" * 1048577)
    os.utime(old, (time.time() - 86400 * 30, time.time() - 86400 * 30))
    action = Action(
        kind="find",
        path=str(tmp_path),
        pattern="*.py",
        min_size_bytes=1048576,
        modified_after=datetime.now(UTC) - timedelta(days=7),
        file_type="file",
    )
    assert list(file_query(action, tmp_path)) == [fresh]


def test_processes_sorted() -> None:
    rows = process_query(5)
    assert 0 < len(rows) <= 5
    assert [row[2] for row in rows] == sorted((row[2] for row in rows), reverse=True)
