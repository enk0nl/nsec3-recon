from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
from .config import normalize_domain

DIRS=['probe','axfr','nsec3map','scheduler/hashcat_logs','scheduler/feedback','scheduler/osint','config','reports']
class Workspace:
    def __init__(self, root:Path, domain:str): self.root=Path(root); self.domain=normalize_domain(domain)
    @classmethod
    def create(cls, domain, out_dir=None):
        d=normalize_domain(domain); ts=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        root=Path(out_dir) if out_dir else Path('runs')/f'{d}-{ts}'
        ws=cls(root,d); ws.root.mkdir(parents=True, exist_ok=True)
        for p in DIRS: (ws.root/p).mkdir(parents=True, exist_ok=True)
        return ws
    def rel(self,p): return str(Path(p).relative_to(self.root))
    def write_json(self, rel, obj):
        p=self.root/rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n', encoding='utf-8'); return p
