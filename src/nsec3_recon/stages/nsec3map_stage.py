from ..adapters.subprocess_runner import SubprocessRunner
from ..adapters.nsec3map import classify_zone_file, detect_command, enumerate_command, parse_detect_output, map_py_path
from ..pipeline import PipelineError

def run(ctx):
    ctx.events.emit("nsec3map", "started", "nsec3map detect-only started")
    src = ctx.config.nsec3map_source_dir
    if not map_py_path(src).exists():
        raise PipelineError("nsec3map", f"nsec3map map.py not found: {map_py_path(src)}")
    dout = ctx.workspace.root / "nsec3map/detect.stdout.log"
    derr = ctx.workspace.root / "nsec3map/detect.stderr.log"
    dres = SubprocessRunner().run(detect_command(src, ctx.config.nsec3map_python, ctx.config.domain), cwd=src, stdout_log=dout, stderr_log=derr)
    detected = parse_detect_output(dout.read_text(errors="ignore"), ctx.config.domain) if dres.returncode == 0 else None
    dobj = {"domain": ctx.config.domain, "status": "success" if detected else "ambiguous", "zone_type": detected, "stdout_log": "nsec3map/detect.stdout.log", "stderr_log": "nsec3map/detect.stderr.log", "exit_code": dres.returncode, "elapsed_seconds": dres.elapsed_seconds}
    ctx.workspace.write_json("nsec3map/detect.json", dobj)
    if not detected:
        ctx.events.emit("nsec3map", "detect_ambiguous", "detect-only was unavailable or ambiguous", "warning", dobj)
    zone = ctx.workspace.root / "nsec3map/zone.txt"
    out = ctx.workspace.root / "nsec3map/map.stdout.log"
    err = ctx.workspace.root / "nsec3map/map.stderr.log"
    cmd = enumerate_command(src, ctx.config.nsec3map_python, ctx.config.domain, zone)
    res = SubprocessRunner().run(cmd, cwd=src, stdout_log=out, stderr_log=err)
    zt = detected or classify_zone_file(zone)
    obj = {"domain": ctx.config.domain, "status": "success" if res.returncode == 0 else "failed", "zone_type": zt, "zone_file": "nsec3map/zone.txt", "stdout_log": "nsec3map/map.stdout.log", "stderr_log": "nsec3map/map.stderr.log", "exit_code": res.returncode, "elapsed_seconds": res.elapsed_seconds}
    ctx.workspace.write_json("nsec3map/map.json", obj)
    ctx.workspace.write_json("nsec3map/result.json", obj)
    ctx.state["nsec3map"] = obj
    if res.returncode != 0:
        ctx.events.emit("nsec3map", "failed", "nsec3map map.py failed", "error", obj)
        raise PipelineError("nsec3map", "nsec3map map.py failed")
    ctx.events.emit("nsec3map", "completed", "nsec3map enumeration completed", data=obj)
    return obj
