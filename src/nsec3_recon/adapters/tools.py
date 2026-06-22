from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import shutil, subprocess
from ..versioning import Version, parse_version, version_at_least, format_version

HASHCAT_MIN = "7.1.2"
AMASS_MIN = "5.1.1"
SUBFINDER_MIN = "2.14.0"

@dataclass
class ToolCheck:
    name: str
    path: str | None
    required: str
    found: Version | None = None
    ok: bool = False
    message: str = ""

    @property
    def version(self) -> str:
        return format_version(self.found)

def resolve_tool(path: str, fallback: str | None = None) -> str | None:
    candidate = Path(path)
    if (candidate.is_absolute() or "/" in path) and candidate.exists():
        return str(candidate)
    found = shutil.which(path)
    if found:
        return found
    if fallback:
        return shutil.which(fallback)
    return None

def _run_version(command: list[str]) -> str:
    try:
        cp = subprocess.run(command, text=True, capture_output=True, timeout=10)
    except Exception:
        return ""
    return (cp.stdout or "") + "\n" + (cp.stderr or "")

def check_hashcat(path: str = "hashcat") -> ToolCheck:
    resolved = resolve_tool(path)
    if not resolved:
        return ToolCheck("hashcat", None, HASHCAT_MIN, message="missing")
    version = parse_version(_run_version([resolved, "--version"]))
    return ToolCheck("hashcat", resolved, HASHCAT_MIN, version, version_at_least(version, HASHCAT_MIN))

def check_amass(path: str = "/home/vboxuser/go/bin/amass") -> ToolCheck:
    resolved = resolve_tool(path, "amass")
    if not resolved:
        return ToolCheck("amass", None, AMASS_MIN, message="missing")
    text = ""
    for flag in ("-version", "version", "--version"):
        text = _run_version([resolved, flag])
        if text.strip():
            break
    version = parse_version(text)
    return ToolCheck("amass", resolved, AMASS_MIN, version, version_at_least(version, AMASS_MIN))

def check_subfinder(path: str = "/home/vboxuser/go/bin/subfinder") -> ToolCheck:
    resolved = resolve_tool(path, "subfinder")
    if not resolved:
        return ToolCheck("subfinder", None, SUBFINDER_MIN, message="missing")
    version = parse_version(_run_version([resolved, "-version"]))
    return ToolCheck("subfinder", resolved, SUBFINDER_MIN, version, version_at_least(version, SUBFINDER_MIN))

def enabled_arm(config: dict, name: str) -> bool:
    for arm in config.get("arms", []):
        if arm.get("name") == name:
            return bool(arm.get("enabled", True))
    return False

def validate_scheduler_tools(config: dict, hashcat_bin: str, amass_bin: str, subfinder_bin: str) -> list[str]:
    errors: list[str] = []
    hc = check_hashcat(hashcat_bin)
    if not hc.ok:
        errors.append(f"hashcat version={hc.version} required>={hc.required} path={hc.path or hashcat_bin}")
    if enabled_arm(config, "osint/amass"):
        am = check_amass(amass_bin)
        if not am.ok:
            errors.append(f"amass version={am.version} required>={am.required} path={am.path or amass_bin}")
    if enabled_arm(config, "osint/subfinder"):
        sf = check_subfinder(subfinder_bin)
        if not sf.ok:
            errors.append(f"subfinder version={sf.version} required>={sf.required} path={sf.path or subfinder_bin}")
    return errors
