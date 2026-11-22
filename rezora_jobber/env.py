import os
from pathlib import Path


def load_env(path: str | Path = Path(__file__).resolve().parent.parent / ".env") -> None:
    """Minimal .env loader (KEY=VALUE lines); real env vars win."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        k, sep, v = line.strip().partition("=")
        if sep and not k.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
