from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import re, shlex

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])$")

def normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower().rstrip(".")
    if not d or not DOMAIN_RE.match(d):
        raise ValueError(f"invalid domain: {domain!r}")
    return d

@dataclass
class PipelineConfig:
    domain: str
    out_dir: Path | None = None
    tui: bool = True
    total_slices: int = 150
    slice_seconds: int = 15
    schedule: str = "adaptive"
    scheduler_config: Path | None = None
    config_template: Path | None = None
    nsec3map_source_dir: Path = Path("deps/src/nsec3map")
    nsec3map_python: str = "python3"
    scheduler_bin: str = "python3 -m nsec3_candidate_scheduler"
    amass_bin: str = "/home/vboxuser/go/bin/amass"
    subfinder_bin: str = "/home/vboxuser/go/bin/subfinder"
    assets_dir: Path = Path("assets")
    dry_run: bool = False
    verbose: bool = False

    def resolved(self):
        self.domain = normalize_domain(self.domain)
        self.assets_dir = Path(self.assets_dir).resolve()
        self.nsec3map_source_dir = Path(self.nsec3map_source_dir)
        if self.out_dir is not None:
            self.out_dir = Path(self.out_dir)
        if self.scheduler_config is not None:
            self.scheduler_config = Path(self.scheduler_config)
        if self.config_template is not None:
            self.config_template = Path(self.config_template)
        return self

    def to_jsonable(self):
        d = asdict(self)
        for k, v in list(d.items()):
            if isinstance(v, Path):
                d[k] = str(v)
        return d

    def scheduler_command(self, workspace: Path, hash_file: Path, config_file: Path):
        return shlex.split(self.scheduler_bin) + [
            "run", "--hashes", str(hash_file), "--hash-mode", "8300", "--config", str(config_file),
            "--out-dir", str(workspace / "scheduler"), "--schedule", self.schedule,
            "--total-slices", str(self.total_slices), "--slice-seconds", str(self.slice_seconds),
        ]
