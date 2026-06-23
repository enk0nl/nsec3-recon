from __future__ import annotations
import json
from importlib.resources import files
from pathlib import Path
from .tools import DEFAULT_AMASS_BIN, DEFAULT_SUBFINDER_BIN, resolve_osint_binary
ASSET_KEYS = {"wordlist", "model", "prefixes", "suffixes"}

def _replace_placeholders(value, domain, amass_value, subfinder_value):
    if isinstance(value, str):
        return value.replace("{{ domain }}", domain).replace("{{ amass_binary }}", amass_value).replace("{{ subfinder_binary }}", subfinder_value)
    if isinstance(value, list):
        return [_replace_placeholders(v, domain, amass_value, subfinder_value) for v in value]
    if isinstance(value, dict):
        return {k: _replace_placeholders(v, domain, amass_value, subfinder_value) for k, v in value.items()}
    return value

def render_scheduler_config(domain, assets_dir, output_path, template_path=None, amass_bin=None, subfinder_bin=None, osint_enabled=True):
    text = (Path(template_path).read_text() if template_path else files("nsec3_recon.templates").joinpath("scheduler_config.json").read_text())
    data = json.loads(text)
    amass_value = resolve_osint_binary(amass_bin or DEFAULT_AMASS_BIN, "amass", DEFAULT_AMASS_BIN)
    subfinder_value = resolve_osint_binary(subfinder_bin or DEFAULT_SUBFINDER_BIN, "subfinder", DEFAULT_SUBFINDER_BIN)
    data = _replace_placeholders(data, domain, amass_value, subfinder_value)
    assets_dir = Path(assets_dir).resolve()
    for arm in data.get("arms", []):
        if not osint_enabled and str(arm.get("name", "")).startswith("osint/"):
            arm["enabled"] = False
        for key in ASSET_KEYS:
            v = arm.get(key)
            if isinstance(v, str) and v.startswith("assets/"):
                arm[key] = str(assets_dir / Path(v).relative_to("assets"))
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")
    return data
