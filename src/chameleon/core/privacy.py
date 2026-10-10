import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


def redact(text: str) -> str:
    text = re.sub(
        r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
        "[PRIVATE KEY REDACTED]",
        text,
        flags=re.S,
    )
    text = re.sub(r"(?i)(authorization\s*[:=]\s*)([^\r\n]+)", r"\1[REDACTED]", text)
    text = re.sub(
        r"(?i)((?:api[_-]?key|token|password|passwd|secret)\s*[:=]\s*)\S+", r"\1[REDACTED]", text
    )
    return re.sub(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{15,})\b", "[REDACTED]", text)


def configure_logging(root: Path, debug: bool = False) -> None:
    directory = root / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        directory / "chameleon.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger = logging.getLogger("chameleon")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
