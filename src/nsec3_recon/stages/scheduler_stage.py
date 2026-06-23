from ..adapters.scheduler import render_scheduler_config
from ..adapters.subprocess_runner import SubprocessRunner
from ..adapters.potfile import extract_potfile_names
from ..events import utc_now
import json
from ..adapters.tools import validate_scheduler_tools
from ..pipeline import PipelineError
from pathlib import Path

MODEL_REQUIRED_ARMS = {
    "feedback/predictive-prefix": ("model",),
    "feedback/predictive-suffix": ("model",),
    "feedback/static-affix-top5000": ("prefixes", "suffixes"),
}


def validate_scheduler_assets(rendered, hash_file=None, amass_bin=None, subfinder_bin=None):
    errors = []
    def require_file(path, label):
        if not path:
            errors.append(f"Missing scheduler asset path for {label}")
            return
        p = Path(path)
        if not p.exists():
            errors.append(f"Missing scheduler asset for {label}: {p}")
        elif p.is_file() and p.stat().st_size == 0:
            errors.append(f"Empty scheduler asset for {label}: {p}")
    if hash_file is not None:
        require_file(hash_file, "hash file")
    for arm in rendered.get("arms", []):
        if arm.get("enabled") is False:
            continue
        name = arm.get("name", "<unnamed>")
        for key in ("wordlist", "model", "prefixes", "suffixes"):
            if key in arm:
                require_file(arm.get(key), f"{name}.{key}")
        if name == "osint/amass" and amass_bin and not Path(str(amass_bin)).expanduser().exists() and "/" in str(amass_bin):
            errors.append(f"Missing OSINT binary for {name}: {amass_bin}")
        if name == "osint/subfinder" and subfinder_bin and not Path(str(subfinder_bin)).expanduser().exists() and "/" in str(subfinder_bin):
            errors.append(f"Missing OSINT binary for {name}: {subfinder_bin}")
    return errors

def validate_model_assets(rendered):
    errors=[]
    for arm in rendered.get("arms", []):
        if arm.get("enabled") is False:
            continue
        for key in MODEL_REQUIRED_ARMS.get(arm.get("name"), ()):
            path=arm.get(key)
            if path and not Path(path).exists():
                errors.append("Missing scheduler model asset: " + str(path) + "\n\nFix:\nscripts/prepare-models.sh\n\nor:\nscripts/prepare-assets.sh")
    return errors

def write_discovery_reports(ctx):
    pot = ctx.workspace.root / "scheduler/run.pot"
    names, malformed = extract_potfile_names(pot)
    reports = ctx.workspace.root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "cracked_names.txt").write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")
    (reports / "discovered_names.txt").write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")
    entries = [{"name": n, "source": "nsec3", "method": "hashcat_potfile", "first_seen_at": utc_now()} for n in names]
    (reports / "discovered_names.json").write_text(json.dumps({"names": entries, "malformed_potfile_lines": malformed}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ctx.state["discovered_names"] = names
    ctx.state["cracked_count"] = len(names)
    ctx.state["discovered_names_count"] = len(names)
    ctx.state["discovered_names_by_source"] = {"nsec3": len(names)}
    ctx.events.emit("discovery", "names_discovered", f"{len(names)} names discovered via NSEC3", data={"source": "nsec3", "count": len(names), "path": "reports/discovered_names.txt", "malformed_potfile_lines": malformed})



def run(ctx):
    ctx.events.emit("scheduler", "started", "scheduler started")
    cfg = (ctx.workspace.root / "config/scheduler_config.json").resolve()
    rendered = render_scheduler_config(
        ctx.config.domain,
        ctx.config.assets_dir,
        cfg,
        ctx.config.scheduler_config or ctx.config.config_template,
        ctx.config.amass_bin,
        ctx.config.subfinder_bin,
        ctx.config.osint_enabled,
    )
    hash_file = (ctx.workspace.root / "nsec3map/nsec3map_hashfile.hash").resolve()
    model_errors = validate_model_assets(rendered)
    if not ctx.config.scheduler_config:
        model_errors = validate_scheduler_assets(rendered, hash_file, ctx.config.amass_bin, ctx.config.subfinder_bin)
    if model_errors:
        message = "; ".join(model_errors)
        ctx.events.emit("scheduler", "model_assets_missing", message, "error", {"errors": model_errors})
        raise PipelineError("scheduler", message)
    ctx.events.emit("scheduler", "model_assets_ok", "scheduler model assets available")
    tool_errors = validate_scheduler_tools(rendered, ctx.config.hashcat_bin, ctx.config.amass_bin, ctx.config.subfinder_bin)
    if tool_errors:
        message = "; ".join(tool_errors)
        ctx.events.emit("scheduler", "tool_preflight_failed", message, "error", {"errors": tool_errors})
        raise PipelineError("scheduler", message)
    cmd = ctx.config.scheduler_command(ctx.workspace.root, hash_file, cfg)
    ctx.state["scheduler_command"] = cmd
    out = ctx.workspace.root / "scheduler/stdout.log"
    err = ctx.workspace.root / "scheduler/stderr.log"
    res = SubprocessRunner().run(
        cmd,
        stdout_log=out,
        stderr_log=err,
        stream=True,
        on_stdout=lambda line: ctx.events.emit("scheduler", "stdout", line),
        on_stderr=lambda line: ctx.events.emit("scheduler", "stderr", line, "warning"),
    )
    ctx.state["scheduler"] = {"exit_code": res.returncode, "elapsed_seconds": res.elapsed_seconds}
    if res.returncode != 0:
        message = "\n".join([
            "Stage scheduler failed.",
            "Command:",
            " ".join(cmd),
            "CWD:",
            "<none>",
            "Exit code:",
            str(res.returncode),
            "Stdout:",
            str(out),
            "Stderr:",
            str(err),
        ])
        raise PipelineError("scheduler", message)
    write_discovery_reports(ctx)
    ctx.events.emit("scheduler", "completed", "scheduler completed")
    return ctx.state["scheduler"]
