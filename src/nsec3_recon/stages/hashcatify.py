from ..adapters.subprocess_runner import SubprocessRunner
from ..adapters.nsec3map import hashcatify_command
from ..pipeline import PipelineError

def run(ctx):
    ctx.events.emit("hashcatify", "started", "hashcatify started")
    zone = ctx.workspace.root / "nsec3map/zone.txt"
    hf = ctx.workspace.root / "nsec3map/nsec3map_hashfile.hash"
    cmd = hashcatify_command(ctx.config.nsec3map_source_dir, ctx.config.nsec3map_python, zone, hf)
    res = SubprocessRunner().run(cmd, stdout_log=ctx.workspace.root / "nsec3map/hashcatify.stdout.log", stderr_log=ctx.workspace.root / "nsec3map/hashcatify.stderr.log")
    count = sum(1 for _ in hf.open()) if hf.exists() else 0
    obj = {"status": "success" if res.returncode == 0 and count else "failed", "hash_file": "nsec3map/nsec3map_hashfile.hash", "hash_count": count, "elapsed_seconds": res.elapsed_seconds, "command": cmd}
    ctx.workspace.write_json("nsec3map/hashcatify.json", obj)
    ctx.state["hashcatify"] = obj
    if obj["status"] != "success":
        ctx.events.emit("hashcatify", "failed", "hashcatify produced no hashes", "error", obj)
        raise PipelineError("hashcatify", "hashcatify produced no hashes")
    ctx.events.emit("hashcatify", "completed", "hashcatify completed", data=obj)
    return obj
