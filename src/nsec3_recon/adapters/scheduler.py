from __future__ import annotations
import json
from importlib.resources import files
from pathlib import Path
from .tools import DEFAULT_AMASS_BIN, DEFAULT_SUBFINDER_BIN, resolve_osint_binary
ASSET_KEYS = {"wordlist", "model", "prefixes", "suffixes"}

def render_scheduler_config(domain, assets_dir, output_path, template_path=None, amass_bin=None, subfinder_bin=None):
    text = (Path(template_path).read_text() if template_path else files("nsec3_recon.templates").joinpath("scheduler_config.json").read_text())
    amass_value = resolve_osint_binary(amass_bin or DEFAULT_AMASS_BIN, "amass", DEFAULT_AMASS_BIN)
    subfinder_value = resolve_osint_binary(subfinder_bin or DEFAULT_SUBFINDER_BIN, "subfinder", DEFAULT_SUBFINDER_BIN)
    text = text.replace("{{ domain }}", domain).replace("{{ amass_binary }}", amass_value).replace("{{ subfinder_binary }}", subfinder_value)
    data = json.loads(text)
    assets_dir = Path(assets_dir).resolve()
    for arm in data.get("arms", []):
        for key in ASSET_KEYS:
            v = arm.get(key)
            if isinstance(v, str) and v.startswith("assets/"):
                arm[key] = str(assets_dir / Path(v).relative_to("assets"))
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")
    return data
