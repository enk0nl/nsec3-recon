from __future__ import annotations
import os
from pathlib import Path


def expand_user_path(path: str) -> str:
    return str(Path(os.path.expandvars(os.path.expanduser(path))).absolute())
