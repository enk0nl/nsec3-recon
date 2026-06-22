from __future__ import annotations
import json
from importlib.resources import files
from pathlib import Path
ASSET_KEYS = {"wordlist", "model", "prefixes", "suffixes"}

def render_scheduler_config(domain, assets_dir, output_path, template_path=None, amass_bin=None, subfinder_bin=None):
    text = (Path(template_path).read_text() if template_path else files("nsec3_recon.templates").joinpath("scheduler_config.json").read_text())
    data = json.loads(text.replace("{{ domain }}", domain))
    assets_dir = Path(assets_dir).resolve()
    for arm in data.get("arms", []):
        for key in ASSET_KEYS:
            v = arm.get(key)
            if isinstance(v, str) and v.startswith("assets/"):
                arm[key] = str(assets_dir / Path(v).relative_to("assets"))
        if arm.get("name") == "osint/amass" and amass_bin:
            arm["amass_binary"] = str(amass_bin)
        if arm.get("name") == "osint/subfinder" and subfinder_bin:
            arm["subfinder_binary"] = str(subfinder_bin)
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")
    return data
