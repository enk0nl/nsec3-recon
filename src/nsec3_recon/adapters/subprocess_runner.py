from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import subprocess, time, threading

@dataclass
class CommandResult:
    command:list[str]; returncode:int; elapsed_seconds:float; stdout_log:str|None=None; stderr_log:str|None=None

class SubprocessRunner:
    def run(self, command, cwd=None, env=None, stdout_log=None, stderr_log=None, timeout=None, on_stdout=None, on_stderr=None, stream=False):
        start=time.time(); outp=Path(stdout_log) if stdout_log else None; errp=Path(stderr_log) if stderr_log else None
        if outp: outp.parent.mkdir(parents=True, exist_ok=True)
        if errp: errp.parent.mkdir(parents=True, exist_ok=True)
        if not stream:
            cp=subprocess.run(command,cwd=cwd,env=env,timeout=timeout,capture_output=True,text=True)
            if outp: outp.write_text(cp.stdout, encoding='utf-8')
            if errp: errp.write_text(cp.stderr, encoding='utf-8')
            return CommandResult(list(command), cp.returncode, time.time()-start, str(outp) if outp else None, str(errp) if errp else None)
        with (outp.open('w',encoding='utf-8') if outp else open('/dev/null','w')) as of, (errp.open('w',encoding='utf-8') if errp else open('/dev/null','w')) as ef:
            p=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
            def pump(src, file, cb):
                for line in src:
                    file.write(line); file.flush()
                    if cb: cb(line.rstrip('\n'))
            t1=threading.Thread(target=pump,args=(p.stdout,of,on_stdout)); t2=threading.Thread(target=pump,args=(p.stderr,ef,on_stderr)); t1.start(); t2.start()
            rc=p.wait(timeout=timeout); t1.join(); t2.join()
        return CommandResult(list(command), rc, time.time()-start, str(outp) if outp else None, str(errp) if errp else None)
