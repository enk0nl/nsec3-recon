from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import signal
import subprocess
import sys
import threading
import time


@dataclass
class CommandResult:
    command: list[str]
    returncode: int
    elapsed_seconds: float
    stdout_log: str | None = None
    stderr_log: str | None = None
    timed_out: bool = False
    interrupted: bool = False
    signal: int | None = None


class SubprocessRunner:
    def _terminate_group(self, process: subprocess.Popen, grace_seconds: float = 2.0) -> tuple[int | None, bool]:
        sig = None
        if process.poll() is not None:
            return sig, False
        try:
            os.killpg(process.pid, signal.SIGTERM)
            sig = signal.SIGTERM
        except ProcessLookupError:
            return sig, False
        except Exception:
            process.terminate()
            sig = signal.SIGTERM
        try:
            process.wait(timeout=grace_seconds)
            return sig, False
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                sig = signal.SIGKILL
            except ProcessLookupError:
                pass
            except Exception:
                process.kill()
                sig = signal.SIGKILL
            process.wait(timeout=grace_seconds)
            return sig, True

    def run(self, command, cwd=None, env=None, stdout_log=None, stderr_log=None, timeout=None, on_stdout=None, on_stderr=None, stream=False):
        start = time.time()
        outp = Path(stdout_log) if stdout_log else None
        errp = Path(stderr_log) if stderr_log else None
        if outp:
            outp.parent.mkdir(parents=True, exist_ok=True)
        if errp:
            errp.parent.mkdir(parents=True, exist_ok=True)

        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            start_new_session=True,
        )

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        def pump(src, sink, chunks, cb):
            try:
                for line in iter(src.readline, ""):
                    chunks.append(line)
                    if sink:
                        sink.write(line)
                        sink.flush()
                    if cb:
                        cb(line.rstrip("\n"))
            finally:
                try:
                    src.close()
                except Exception:
                    pass

        stdout_sink = outp.open("w", encoding="utf-8") if outp else None
        stderr_sink = errp.open("w", encoding="utf-8") if errp else None
        try:
            t1 = threading.Thread(target=pump, args=(process.stdout, stdout_sink, stdout_chunks, on_stdout if stream else None), daemon=True)
            t2 = threading.Thread(target=pump, args=(process.stderr, stderr_sink, stderr_chunks, on_stderr if stream else None), daemon=True)
            t1.start(); t2.start()
            try:
                rc = process.wait(timeout=timeout)
                timed_out = False
                interrupted = False
                sig = -rc if rc < 0 else None
            except subprocess.TimeoutExpired:
                sig, _ = self._terminate_group(process)
                rc = process.returncode if process.returncode is not None else -int(sig or signal.SIGKILL)
                timed_out = True
                interrupted = False
            except KeyboardInterrupt:
                sig, _ = self._terminate_group(process)
                raise
            finally:
                t1.join(timeout=2)
                t2.join(timeout=2)
            if outp is None and stdout_chunks:
                pass
            if errp is None and stderr_chunks:
                pass
            return CommandResult(list(command), rc, time.time() - start, str(outp) if outp else None, str(errp) if errp else None, timed_out, interrupted, sig)
        finally:
            if stdout_sink:
                stdout_sink.close()
            if stderr_sink:
                stderr_sink.close()
