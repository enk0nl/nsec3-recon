from __future__ import annotations
from ..adapters.subprocess_runner import SubprocessRunner
from ..adapters.nsec3map import classify_zone_file, detect_command, detect_indicates_not_dnssec, enumerate_command, parse_detect_output, map_py_path
from ..pipeline import PipelineError


def _format_subprocess_failure(stage, command, cwd, result, stderr_log, stdout_log=None, interpreter=None):
    lines = [
        f"Stage {stage} failed.",
        "Command:",
        " ".join(str(x) for x in command),
        "CWD:",
        str(cwd) if cwd else "<none>",
        "Exit code:",
        str(result.returncode),
    ]
    if stdout_log:
        lines += ["Stdout:", str(stdout_log)]
    if stderr_log:
        lines += ["Stderr:", str(stderr_log)]
        stderr_text = stderr_log.read_text(errors="ignore") if stderr_log.exists() else ""
        if "No module named 'psycopg2'" in stderr_text or "No module named psycopg2" in stderr_text:
            py = interpreter or command[0]
            lines += [
                "",
                "nsec3map failed because psycopg2 is missing from the Python interpreter used to run map.py.",
                f"Interpreter: {py}",
                f"Fix: {py} -m pip install psycopg2-binary",
            ]
    return "\n".join(lines)


def ensure_python_deps(ctx):
    cmd = [ctx.config.nsec3map_python, "-c", "import dns, psycopg2"]
    out = ctx.workspace.root / "nsec3map/python-deps.stdout.log"
    err = ctx.workspace.root / "nsec3map/python-deps.stderr.log"
    res = SubprocessRunner().run(cmd, stdout_log=out, stderr_log=err)
    obj = {"command": cmd, "exit_code": res.returncode, "stdout_log": "nsec3map/python-deps.stdout.log", "stderr_log": "nsec3map/python-deps.stderr.log"}
    ctx.workspace.write_json("nsec3map/python-deps.json", obj)
    if res.returncode != 0:
        msg = (
            "nsec3map dependencies are missing from the Python interpreter used to run map.py.\n\n"
            f"Interpreter: {ctx.config.nsec3map_python}\n\n"
            f"Fix: {ctx.config.nsec3map_python} -m pip install dnspython psycopg2-binary\n\n"
            "If using the project venv:\nsource .venv/bin/activate\npython -m pip install dnspython psycopg2-binary"
        )
        ctx.events.emit("nsec3map", "python_deps_missing", msg, "error", obj)
        raise PipelineError("nsec3map", msg)
    ctx.events.emit("nsec3map", "python_deps_ok", "nsec3map Python dependencies available", "debug", {"interpreter": ctx.config.nsec3map_python})
    return obj


def detect(ctx):
    ctx.events.emit("nsec3map", "detect_started", "nsec3map detect-only started")
    src = ctx.config.nsec3map_source_dir
    if not map_py_path(src).exists():
        raise PipelineError("nsec3map", f"nsec3map map.py not found: {map_py_path(src)}")
    ensure_python_deps(ctx)
    dout = ctx.workspace.root / "nsec3map/detect.stdout.log"
    derr = ctx.workspace.root / "nsec3map/detect.stderr.log"
    cmd = detect_command(src, ctx.config.nsec3map_python, ctx.config.domain)
    res = SubprocessRunner().run(cmd, cwd=src, stdout_log=dout, stderr_log=derr)
    stdout = dout.read_text(errors="ignore") if dout.exists() else ""
    stderr = derr.read_text(errors="ignore") if derr.exists() else ""
    detected = parse_detect_output(stdout, ctx.config.domain) if res.returncode == 0 else None
    if detected:
        status = "success"
        zone_type = detected
    elif detect_indicates_not_dnssec(stdout + "\n" + stderr):
        status = "not_dnssec"
        zone_type = "none"
    else:
        status = "ambiguous" if res.returncode == 0 else "failed"
        zone_type = None
    obj = {
        "domain": ctx.config.domain,
        "status": status,
        "zone_type": zone_type,
        "stdout_log": "nsec3map/detect.stdout.log",
        "stderr_log": "nsec3map/detect.stderr.log",
        "exit_code": res.returncode,
        "elapsed_seconds": res.elapsed_seconds,
    }
    ctx.workspace.write_json("nsec3map/detect.json", obj)
    ctx.state["nsec3map_detect"] = obj
    if res.returncode != 0:
        msg = _format_subprocess_failure("nsec3map", cmd, src, res, derr, dout, ctx.config.nsec3map_python)
        ctx.events.emit("nsec3map", "detect_failed", msg, "error", obj)
        raise PipelineError("nsec3map", msg)
    if status == "success":
        ctx.events.emit("nsec3map", "detect_completed", f"detected zone_type={zone_type}", data=obj)
    elif status == "not_dnssec":
        ctx.events.emit("nsec3map", "detect_not_dnssec", "nsec3map detect-only did not report DNSSEC", "warning", obj)
    else:
        ctx.events.emit("nsec3map", "detect_ambiguous", "detect-only failed or was ambiguous", "warning", obj)
    return obj


def enumerate(ctx, detected_zone_type=None):
    ctx.events.emit("nsec3map", "started", "nsec3map enumeration started")
    src = ctx.config.nsec3map_source_dir
    if not map_py_path(src).exists():
        raise PipelineError("nsec3map", f"nsec3map map.py not found: {map_py_path(src)}")
    ensure_python_deps(ctx)
    zone = ctx.workspace.root / "nsec3map/zone.txt"
    out = ctx.workspace.root / "nsec3map/map.stdout.log"
    err = ctx.workspace.root / "nsec3map/map.stderr.log"
    cmd = enumerate_command(src, ctx.config.nsec3map_python, ctx.config.domain, zone)
    res = SubprocessRunner().run(cmd, cwd=src, stdout_log=out, stderr_log=err)
    zt = detected_zone_type if detected_zone_type in {"nsec", "nsec3"} else classify_zone_file(zone)
    obj = {
        "domain": ctx.config.domain,
        "status": "success" if res.returncode == 0 else "failed",
        "zone_type": zt,
        "zone_file": "nsec3map/zone.txt",
        "stdout_log": "nsec3map/map.stdout.log",
        "stderr_log": "nsec3map/map.stderr.log",
        "exit_code": res.returncode,
        "elapsed_seconds": res.elapsed_seconds,
        "command": cmd,
        "cwd": str(src),
    }
    ctx.workspace.write_json("nsec3map/map.json", obj)
    ctx.workspace.write_json("nsec3map/result.json", obj)
    ctx.state["nsec3map"] = obj
    if res.returncode != 0:
        msg = _format_subprocess_failure("nsec3map", cmd, src, res, err, out, ctx.config.nsec3map_python)
        ctx.events.emit("nsec3map", "failed", msg, "error", obj)
        raise PipelineError("nsec3map", msg)
    ctx.events.emit("nsec3map", "completed", "nsec3map enumeration completed", data=obj)
    return obj


def run(ctx):
    det = detect(ctx)
    return enumerate(ctx, det.get("zone_type"))
