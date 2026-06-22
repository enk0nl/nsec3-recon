from ..adapters.subprocess_runner import SubprocessRunner
from ..adapters.nsec3map import hashcatify_command
from ..pipeline import PipelineError
from .nsec3map_stage import _format_subprocess_failure


def run(ctx):
    ctx.events.emit("hashcatify", "started", "hashcatify started")
    zone = (ctx.workspace.root / "nsec3map/zone.txt").resolve()
    hf = (ctx.workspace.root / "nsec3map/nsec3map_hashfile.hash").resolve()
    hf.parent.mkdir(parents=True, exist_ok=True)
    cmd = hashcatify_command(ctx.config.nsec3map_source_dir, ctx.config.nsec3map_python, zone, hf)
    out = ctx.workspace.root / "nsec3map/hashcatify.stdout.log"
    err = ctx.workspace.root / "nsec3map/hashcatify.stderr.log"
    res = SubprocessRunner().run(cmd, stdout_log=out, stderr_log=err)
    count = sum(1 for _ in hf.open()) if hf.exists() else 0
    obj = {"status": "success" if res.returncode == 0 and count else "failed", "hash_file": "nsec3map/nsec3map_hashfile.hash", "hash_count": count, "elapsed_seconds": res.elapsed_seconds, "command": cmd}
    ctx.workspace.write_json("nsec3map/hashcatify.json", obj)
    ctx.state["hashcatify"] = obj
    if obj["status"] != "success":
        msg = _format_subprocess_failure("hashcatify", cmd, None, res, err, out, ctx.config.nsec3map_python)
        if res.returncode == 0 and not count:
            msg = "hashcatify produced no hashes\n" + msg
        ctx.events.emit("hashcatify", "failed", msg, "error", obj)
        raise PipelineError("hashcatify", msg)
    ctx.events.emit("hashcatify", "completed", "hashcatify completed", data=obj)
    return obj
