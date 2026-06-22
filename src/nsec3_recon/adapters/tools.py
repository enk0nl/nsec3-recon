from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import shutil, subprocess
from ..paths import expand_user_path
from ..versioning import Version, parse_version, version_at_least, format_version

HASHCAT_MIN = "7.1.2"
AMASS_MIN = "5.1.1"
SUBFINDER_MIN = "2.14.0"
DEFAULT_AMASS_BIN = "~/go/bin/amass"
DEFAULT_SUBFINDER_BIN = "~/go/bin/subfinder"

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
    expanded = expand_user_path(path) if path.startswith(("~", "$")) or "/" in path else path
    candidate = Path(expanded)
    if (candidate.is_absolute() or "/" in expanded) and candidate.exists():
        return str(candidate)
    found = shutil.which(expanded)
    if found:
        return found
    if fallback:
        return shutil.which(fallback)
    return None

def resolve_osint_binary(configured: str, tool_name: str, default_home_path: str) -> str:
    expanded = expand_user_path(configured)
    default_expanded = expand_user_path(default_home_path)
    if configured != default_home_path:
        return expanded if (configured.startswith(("~", "$")) or "/" in configured) else configured
    if Path(default_expanded).exists():
        return default_expanded
    if shutil.which(tool_name):
        return tool_name
    return tool_name

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

def check_amass(path: str = DEFAULT_AMASS_BIN) -> ToolCheck:
    resolved = resolve_tool(path, "amass")
    if not resolved and path == DEFAULT_AMASS_BIN:
        resolved = shutil.which("amass")
    if not resolved:
        return ToolCheck("amass", None, AMASS_MIN, message="missing")
    text = ""
    for flag in ("-version", "version", "--version"):
        text = _run_version([resolved, flag])
        if text.strip():
            break
    version = parse_version(text)
    return ToolCheck("amass", resolved, AMASS_MIN, version, version_at_least(version, AMASS_MIN))

def check_subfinder(path: str = DEFAULT_SUBFINDER_BIN) -> ToolCheck:
    resolved = resolve_tool(path, "subfinder")
    if not resolved and path == DEFAULT_SUBFINDER_BIN:
        resolved = shutil.which("subfinder")
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
