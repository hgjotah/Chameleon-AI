import json
import os
import time
from pathlib import Path

from chameleon.core.sessions import SessionStore


def test_session_redaction_expiry_and_identity(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, os.getpid())
    for index in range(9):
        store.remember(f"request {index} token=private-value")
    assert len(store.recent()) == 6
    assert "private-value" not in store.path.read_text()
    record = json.loads(store.path.read_text())
    record["created"] += 1
    store.path.write_text(json.dumps(record))
    assert not store.recent()
    store.cleanup()
    assert not store.path.exists()
    store.remember("temporary context")
    record = json.loads(store.path.read_text())
    record["updated"] = time.time() - 1801
    store.path.write_text(json.dumps(record))
    assert not store.recent()
    store.cleanup()
    assert not store.path.exists()
