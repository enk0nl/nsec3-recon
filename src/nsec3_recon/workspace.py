from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, uuid
from importlib.metadata import version, PackageNotFoundError
from .config import normalize_domain

DIRS=['probe','axfr','nsec3map','scheduler/hashcat_logs','scheduler/feedback','scheduler/osint','config','reports']
class Workspace:
    def __init__(self, root:Path, domain:str): self.root=Path(root); self.domain=normalize_domain(domain)
    @classmethod
    def create(cls, domain, out_dir=None):
        d=normalize_domain(domain); now=datetime.now(timezone.utc); ts=now.strftime('%Y%m%d-%H%M%S'); suffix=uuid.uuid4().hex[:4]
        run_id=f'{d}-{ts}-{suffix}'
        root=(Path(out_dir) if out_dir else Path('runs')/run_id).resolve()
        ws=cls(root,d); ws.root.mkdir(parents=True, exist_ok=True)
        for p in DIRS: (ws.root/p).mkdir(parents=True, exist_ok=True)
        try:
            ver=version('nsec3-recon')
        except PackageNotFoundError:
            ver='0.0.0+local'
        ws.run_metadata={'run_id': run_id if out_dir is None else root.name, 'domain': d, 'created_at': now.replace(microsecond=0).isoformat().replace('+00:00','Z'), 'workspace': str(root), 'nsec3_recon_version': ver}
        ws.write_json('config/run.json', ws.run_metadata)
        return ws
    def rel(self,p): return str(Path(p).relative_to(self.root))
    def write_json(self, rel, obj):
        p=self.root/rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n', encoding='utf-8'); return p
