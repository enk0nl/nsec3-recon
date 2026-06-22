from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
import json

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
        for cb in self.listeners: cb(ev)
        return ev
