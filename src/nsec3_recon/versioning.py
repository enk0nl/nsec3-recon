from __future__ import annotations
import re

Version = tuple[int, int, int]

def parse_version(text: str) -> Version | None:
    match = re.search(r"\bv?(\d+)\.(\d+)\.(\d+)\b", text or "", re.IGNORECASE)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]

def version_at_least(found: Version | str | None, required: Version | str) -> bool:
    if isinstance(found, str):
        found = parse_version(found)
    if isinstance(required, str):
        required = parse_version(required)
    if found is None or required is None:
        return False
    return found >= required

def format_version(version: Version | None) -> str:
    return "unknown" if version is None else ".".join(str(part) for part in version)
