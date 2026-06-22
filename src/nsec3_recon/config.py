from __future__ import annotations
from dataclasses import dataclass, asdict, field
from pathlib import Path
import re, shlex, sys

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
    nsec3map_python: str = field(default_factory=lambda: sys.executable)
    scheduler_bin: str = "python3 -m nsec3_candidate_scheduler"
    hashcat_bin: str = "hashcat"
    amass_bin: str = "~/go/bin/amass"
    subfinder_bin: str = "~/go/bin/subfinder"
    assets_dir: Path = Path("assets")
    dry_run: bool = False
    verbose: bool = False
    tools: dict = field(default_factory=dict)

    def resolved(self):
        self.domain = normalize_domain(self.domain)
        self.assets_dir = Path(self.assets_dir).resolve()
        self.nsec3map_source_dir = Path(self.nsec3map_source_dir).resolve()
        if self.out_dir is not None:
            self.out_dir = Path(self.out_dir)
        if self.scheduler_config is not None:
            self.scheduler_config = Path(self.scheduler_config)
        if self.config_template is not None:
            self.config_template = Path(self.config_template)
        return self

    def to_jsonable(self):
        d = asdict(self)
        d["tools"] = {"hashcat": {"path": self.hashcat_bin, "min_version": "7.1.2"}, "amass": {"path": self.amass_bin, "min_version": "5.1.1", "required_if_arm_enabled": True}, "subfinder": {"path": self.subfinder_bin, "min_version": "2.14.0", "required_if_arm_enabled": True}}
        for k, v in list(d.items()):
            if isinstance(v, Path):
                d[k] = str(v)
        return d

    def scheduler_command(self, workspace: Path, hash_file: Path, config_file: Path):
        workspace = Path(workspace).resolve()
        hash_file = Path(hash_file).resolve()
        config_file = Path(config_file).resolve()
        scheduler_dir = (workspace / "scheduler").resolve()
        scheduler_dir.mkdir(parents=True, exist_ok=True)
        return shlex.split(self.scheduler_bin) + [
            "run", "--hashes", str(hash_file), "--hash-mode", "8300", "--config", str(config_file),
            "--out-dir", str(scheduler_dir), "--schedule", self.schedule,
            "--total-slices", str(self.total_slices), "--slice-seconds", str(self.slice_seconds),
        ]
