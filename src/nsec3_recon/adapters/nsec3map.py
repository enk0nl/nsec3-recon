from __future__ import annotations
from pathlib import Path
import re

def map_py_path(source_dir: Path) -> Path:
    return Path(source_dir) / "map.py"

def detect_command(source_dir: Path, python: str, domain: str) -> list[str]:
    return [python, "map.py", "--detect-only", domain]

def enumerate_command(source_dir: Path, python: str, domain: str, zone_file: Path) -> list[str]:
    return [python, "map.py", f"--output={zone_file}", domain]

def parse_detect_output(stdout: str, domain: str) -> str | None:
    wanted = domain.rstrip(".").lower()
    for line in stdout.splitlines():
        m = re.match(r"^\s*(?P<domain>[^:\s]+)\s*:\s*(?P<mode>nsec3|nsec)\b", line.lower())
        if m and m.group("domain").rstrip(".") == wanted:
            return m.group("mode")
    return None

def detect_indicates_not_dnssec(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "no dnssec", "not dnssec", "not signed", "unsigned",
        "does not use dnssec", "no nsec", "no nsec3",
    )
    return any(marker in lowered for marker in markers)

def classify_zone_file(path):
    text = Path(path).read_text(encoding="utf-8", errors="ignore").upper() if Path(path).exists() else ""
    if " NSEC3 " in text or "\tNSEC3\t" in text:
        return "nsec3"
    if " NSEC " in text or "\tNSEC\t" in text:
        return "nsec"
    return "unknown"

def find_hashcatify_script(source_dir: Path) -> Path | None:
    base = Path(source_dir)
    for rel in ("hashcatify.py", "n3map/hashcatify.py"):
        p = base / rel
        if p.exists():
            return p
    return None

def hashcatify_command(source_dir: Path, python: str, zone_file: Path, hash_file: Path) -> list[str]:
    script = find_hashcatify_script(source_dir)
    if script:
        return [python, str(script), str(zone_file), str(hash_file)]
    return [python, "-m", "n3map.hashcatify", str(zone_file), str(hash_file)]

def extract_nsec_names(path, domain):
    names = []
    seen = set()
    dom = domain.rstrip(".")
    for line in Path(path).read_text(errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith(";"):
            continue
        owner = s.split()[0].rstrip(".").lower()
        if owner == "@":
            owner = dom
        elif not owner.endswith(dom):
            owner = f"{owner}.{dom}" if "." not in owner else owner
        if owner.endswith(dom) and owner not in seen:
            seen.add(owner)
            names.append(owner)
    return names
