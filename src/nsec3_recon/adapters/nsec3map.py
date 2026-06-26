from __future__ import annotations
from pathlib import Path
import re

def map_py_path(source_dir: Path) -> Path:
    return Path(source_dir) / "map.py"

def detect_command(source_dir: Path, python: str, domain: str) -> list[str]:
    return [python, "map.py", "--detect-only", domain]

def enumerate_command(source_dir: Path, python: str, domain: str, zone_file: Path, hashlimit: int = 0) -> list[str]:
    zone_file = Path(zone_file).resolve()
    zone_file.parent.mkdir(parents=True, exist_ok=True)
    return [python, "map.py", f"--output={zone_file}", f"--hashlimit={int(hashlimit)}", domain]

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
    zone_file = Path(zone_file).resolve()
    hash_file = Path(hash_file).resolve()
    hash_file.parent.mkdir(parents=True, exist_ok=True)
    script = find_hashcatify_script(source_dir)
    if script:
        return [python, str(script.resolve()), str(zone_file), str(hash_file)]
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


class NSEC3ChainRow(dict):
    pass


def _owner_hash(owner: str, domain: str) -> str:
    owner = str(owner or '').strip().rstrip('.').lower()
    zone = str(domain or '').strip().rstrip('.').lower()
    if zone and owner.endswith('.' + zone):
        owner = owner[:-(len(zone) + 1)]
    return owner.split('.', 1)[0]


def parse_nsec3_chain_rows(path, domain=''):
    rows = []
    seen = set()
    p = Path(path)
    if not p.exists():
        return rows
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        s = line.strip()
        if not s or s.startswith(';'):
            continue
        parts = s.split()
        try:
            idx = next(i for i, part in enumerate(parts) if part.upper() == 'NSEC3')
        except StopIteration:
            continue
        owner = _owner_hash(parts[0], domain)
        if not owner or owner in seen:
            continue
        seen.add(owner)
        fields = parts[idx + 1:]
        row = NSEC3ChainRow(hash=owner)
        for key, pos in (('algorithm', 0), ('flags', 1), ('iterations', 2), ('salt', 3), ('next_hash', 4)):
            row[key] = fields[pos] if len(fields) > pos else ''
        row['rrtypes'] = ' '.join(fields[5:]) if len(fields) > 5 else ''
        rows.append(row)
    return rows
