from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import traceback

@dataclass
class PipelineEvent:
    ts: str
    stage: str
    level: str
    event: str
    message: str
    data: dict = field(default_factory=dict)

def utc_now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

class EventSink:
    def __init__(self, path:Path, listeners=None):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self.listeners=listeners or []
    def emit(self, stage, event, message, level='info', data=None):
        ev=PipelineEvent(utc_now(), stage, level, event, message, data or {})
        with self.path.open('a', encoding='utf-8') as f: f.write(json.dumps(asdict(ev), sort_keys=True)+'\n')
        for cb in list(self.listeners):
            try:
                cb(ev)
            except Exception as exc:
                self._record_listener_error(cb, exc)
        return ev

    def _record_listener_error(self, cb, exc):
        msg = f"{utc_now()} listener={getattr(cb, '__name__', repr(cb))} error={exc!r}\n"
        try:
            log = self.path.parent / "logs" / "listener_errors.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a", encoding="utf-8") as f:
                f.write(msg)
                traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
        except Exception:
            print(msg, file=sys.stderr)
