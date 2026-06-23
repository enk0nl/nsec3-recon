from __future__ import annotations
import json, threading, time
from pathlib import Path
from .dashboard_state import DashboardState
from .scheduler_parser import normalize_scheduler_record, parse_scheduler_line
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
    def __init__(self, domain='', workspace=None, refresh_per_second=2.0, console=None, potfile_poll_interval_seconds=1.0):
        self.state=DashboardState(domain, workspace); self.refresh_per_second=min(float(refresh_per_second), 10.0); self._lock=threading.RLock(); self._stop=threading.Event(); self._thread=None; self._live=None; self._tail=None; self._jobs_tail=None; self._dirty=True
        self.console=console; self.potfile_poll_interval_seconds=potfile_poll_interval_seconds; self._last_potfile_poll=0.0
    def start(self):
        from rich.live import Live
        self._live=Live(self.render(), refresh_per_second=self.refresh_per_second, console=self.console, transient=False, screen=False, auto_refresh=False)
        self._live.start()
        self._thread=threading.Thread(target=self._loop, daemon=True); self._thread.start()
    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=2)
        if self._live:
            with self._lock: self._live.update(self.render(), refresh=True)
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
                parsed=parse_scheduler_line(event.message)
                if parsed.parsed: self.state.update_slice(parsed.data)
                else:
                    self.state.recent_scheduler_messages.append(parsed.data['message']); self.state.add_activity(parsed.data['message'])
            self._dirty=True
    def poll_external_sources(self):
        now=time.monotonic()
        if now - self._last_potfile_poll < self.potfile_poll_interval_seconds:
            return
        self._last_potfile_poll=now
        if self._jobs_tail is None:
            jobs=discover_jobs_jsonl(self.state.workspace)
            if jobs: self._jobs_tail=JsonlTail(jobs)
        if self._jobs_tail:
            for record in self._jobs_tail.poll():
                normalized=normalize_scheduler_record(record)
                if normalized and self.state.update_slice(normalized.data): self._dirty=True
        if self._tail is None:
            path=self.state.current_potfile_path or discover_potfile(self.state.workspace)
            if path:
                self.state.current_potfile_path=str(path); self._tail=PotfileTail(path)
        if self._tail:
            new=self._tail.poll()
            if self.state.add_discovered_names(new, source='nsec3', method='hashcat_potfile'): self._dirty=True
