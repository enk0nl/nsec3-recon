from __future__ import annotations
import json, threading, time
from pathlib import Path
from .dashboard_state import DashboardState
from .scheduler_parser import normalize_scheduler_record, normalize_scheduler_status_record, parse_osint_events, parse_scheduler_line
from .widgets import build_dashboard
from ..adapters.potfile import PotfileTail

DASHBOARD_MODES={'auto','rich','plain','off'}

def rich_available() -> bool:
    try:
        import rich  # noqa: F401
        return True
    except Exception:
        return False

def resolve_dashboard_mode(mode: str='auto', stdout_isatty: bool=False, rich_is_available: bool|None=None) -> str:
    if mode not in DASHBOARD_MODES: raise ValueError(f"invalid dashboard mode: {mode}")
    if mode in {'plain','off'}: return mode
    avail = rich_available() if rich_is_available is None else rich_is_available
    if mode == 'rich': return 'rich' if avail else 'plain'
    return 'rich' if stdout_isatty and avail else 'plain'

class TextTail:
    def __init__(self, path):
        self.path=Path(path); self.offset=0
    def poll_text(self):
        if not self.path.exists(): return ""
        with self.path.open('r', encoding='utf-8', errors='ignore') as f:
            f.seek(self.offset); text=f.read(); self.offset=f.tell()
        return text

class LineTail:
    def __init__(self, path):
        self.path=Path(path); self.offset=0
    def poll(self):
        if not self.path.exists(): return []
        with self.path.open('r', encoding='utf-8', errors='ignore') as f:
            f.seek(self.offset); lines=f.readlines(); self.offset=f.tell()
        return [line.rstrip('\n') for line in lines if line.strip()]

class JsonlTail:
    def __init__(self, path):
        self.path=Path(path); self.offset=0
    def poll(self):
        if not self.path.exists(): return []
        out=[]
        with self.path.open('r', encoding='utf-8', errors='ignore') as f:
            f.seek(self.offset); lines=f.readlines(); self.offset=f.tell()
        for line in lines:
            line=line.strip()
            if not line: continue
            try: out.append(json.loads(line))
            except json.JSONDecodeError: continue
        return out

def discover_jobs_jsonl(workspace) -> Path | None:
    path=Path(workspace)/'scheduler/jobs.jsonl'
    return path if path.exists() else None

def discover_potfile(workspace) -> Path | None:
    root=Path(workspace)/'scheduler'
    names=('*.potfile','*.pot','hashcat.potfile','hashcat.pot','run.pot','potfile.txt')
    if not root.exists(): return None
    for pat in names:
        for p in root.rglob(pat):
            if p.is_file(): return p
    return None

class RichDashboard:
    def __init__(self, domain='', workspace=None, refresh_per_second=2.0, console=None, potfile_poll_interval_seconds=1.0, scheduler_total_slices=None, verbose: bool = False, jobs_poll_interval_seconds=0.25, stdout_poll_interval_seconds=0.25):
        self.state=DashboardState(domain, workspace, scheduler_total_slices=scheduler_total_slices, verbose=verbose); self.refresh_per_second=min(float(refresh_per_second), 10.0); self._lock=threading.RLock(); self._stop=threading.Event(); self._thread=None; self._live=None; self._tail=None; self._jobs_tail=None; self._stdout_tail=None; self._dirty=True
        self.console=console; self.potfile_poll_interval_seconds=potfile_poll_interval_seconds; self.jobs_poll_interval_seconds=(0 if potfile_poll_interval_seconds == 0 else jobs_poll_interval_seconds); self.stdout_poll_interval_seconds=(0 if potfile_poll_interval_seconds == 0 else stdout_poll_interval_seconds); self._last_potfile_poll=0.0; self._last_jobs_poll=0.0; self._last_stdout_poll=0.0
    def start(self):
        from rich.live import Live
        self._live=Live(self.render(), refresh_per_second=self.refresh_per_second, console=self.console, transient=False, screen=False, auto_refresh=False)
        self._live.start()
        self._thread=threading.Thread(target=self._loop, daemon=True); self._thread.start()
    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=2)
        self.final_refresh()
        if self._live:
            self._live.stop()
    def _loop(self):
        interval=1/max(self.refresh_per_second,1)
        while not self._stop.wait(interval):
            with self._lock:
                self.poll_external_sources()
                if self._dirty: self.refresh()
    def refresh(self):
        if self._live: self._live.update(self.render(), refresh=True)
        self._dirty=False
    def render(self): return build_dashboard(self.state)
    def handle_event(self,event):
        with self._lock:
            self.state.handle_event(event)
            if event.stage=='scheduler' and event.event=='stdout':
                osint_events=parse_osint_events(event.message)
                for osint in osint_events:
                    if self.state.update_osint_status(osint):
                        self._dirty=True
                parsed=parse_scheduler_line(event.message)
                if parsed.parsed:
                    self.state.latest_stdout_slice_debug = parsed.data
                elif not osint_events:
                    self.state.recent_scheduler_messages.append(parsed.data['message']); self.state.add_activity(parsed.data['message'])
            self._dirty=True
    def poll_external_sources(self, force: bool = False):
        self._poll_jobs_jsonl(force=force)
        self._poll_scheduler_stdout_log(force=force)
        self._poll_potfile(force=force)

    def final_refresh(self):
        with self._lock:
            self.poll_external_sources(force=True)
            self.refresh()

    def _poll_jobs_jsonl(self, force: bool = False):
        now=time.monotonic()
        if not force and now - self._last_jobs_poll < self.jobs_poll_interval_seconds:
            return
        self._last_jobs_poll=now
        if self._jobs_tail is None:
            jobs=discover_jobs_jsonl(self.state.workspace)
            if jobs: self._jobs_tail=JsonlTail(jobs)
        if self._jobs_tail:
            for record in self._jobs_tail.poll():
                normalized=normalize_scheduler_record(record)
                if normalized and self.state.update_scheduler_job(normalized.data): self._dirty=True
                if self.state.update_scheduler_completion(record): self._dirty=True
                status=normalize_scheduler_status_record(record)
                if status and self.state.update_arm_status(status.data): self._dirty=True

    def _poll_scheduler_stdout_log(self, force: bool = False):
        now=time.monotonic()
        if not force and now - self._last_stdout_poll < self.stdout_poll_interval_seconds:
            return
        self._last_stdout_poll=now
        if self._stdout_tail is None:
            scheduler_dir=Path(self.state.workspace)/'scheduler'
            for name in ('stdout.log', 'scheduler.stdout.log', 'scheduler_stdout.log'):
                stdout_path=scheduler_dir/name
                if stdout_path.exists():
                    self._stdout_tail=TextTail(stdout_path)
                    break
        if self._stdout_tail:
            text=self._stdout_tail.poll_text()
            for osint in parse_osint_events(text):
                osint['source']='stdout_log'
                if self.state.update_osint_status(osint): self._dirty=True

    def _poll_potfile(self, force: bool = False):
        now=time.monotonic()
        if not force and now - self._last_potfile_poll < self.potfile_poll_interval_seconds:
            return
        self._last_potfile_poll=now
        if self._tail is None:
            path=self.state.current_potfile_path or discover_potfile(self.state.workspace)
            if path:
                self.state.current_potfile_path=str(path); self._tail=PotfileTail(path)
        if self._tail:
            new=self._tail.poll()
            if getattr(self._tail, 'cracked_count', 0) > self.state.nsec3_hash_cracked:
                self.state.nsec3_hash_cracked = self._tail.cracked_count; self._dirty=True
            if self.state.add_discovered_names(new, source='nsec3', method='hashcat_potfile'): self._dirty=True
