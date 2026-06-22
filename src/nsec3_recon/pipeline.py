from __future__ import annotations
from dataclasses import dataclass, field
import time
from pathlib import Path
from .config import PipelineConfig
from .workspace import Workspace
from .events import EventSink
from .report import write_summary

class PipelineError(Exception):
    def __init__(self, stage, message): super().__init__(message); self.stage=stage; self.message=message

@dataclass
class PipelineContext:
    config: PipelineConfig; workspace: Workspace; events: EventSink; started_at: float=field(default_factory=time.time); state: dict=field(default_factory=dict)

class Pipeline:
    def __init__(self, config:PipelineConfig): self.config=config.resolved(); self.ctx=None
    def setup(self):
        ws=Workspace.create(self.config.domain, self.config.out_dir); ev=EventSink(ws.root/'events.jsonl')
        self.ctx=PipelineContext(self.config,ws,ev); return self.ctx
    def run(self):
        from .stages import preflight,dns_probe,axfr,nsec3map_stage,hashcatify,scheduler_stage
        from .adapters.scheduler import render_scheduler_config
        from .adapters.nsec3map import extract_nsec_names
        ctx=self.setup()
        try:
            preflight.run(ctx)
            render_scheduler_config(ctx.config.domain, ctx.config.assets_dir, ctx.workspace.root/'config/scheduler_config.json', ctx.config.scheduler_config or ctx.config.config_template)
            if ctx.config.dry_run:
                hf=ctx.workspace.root/'nsec3map/nsec3map_hashfile.hash'; sc=ctx.workspace.root/'config/scheduler_config.json'
                print('Planned commands:')
                print(' '.join([ctx.config.nsec3map_python, 'map.py', '--detect-only', ctx.config.domain]))
                print(' '.join([ctx.config.nsec3map_python, 'map.py', f"--output={ctx.workspace.root/'nsec3map/zone.txt'}", ctx.config.domain]))
                print(' '.join([ctx.config.nsec3map_python, '<hashcatify.py>', str(ctx.workspace.root/'nsec3map/zone.txt'), str(hf)]))
                print(' '.join(ctx.config.scheduler_command(ctx.workspace.root,hf,sc)))
                write_summary(ctx,'dry_run'); return ctx
            dns_probe.run(ctx); ax=axfr.run(ctx)
            if ax.get('supported'): write_summary(ctx,'axfr'); return ctx
            if not ctx.state.get('dnssec',{}).get('dnssec_enabled'):
                ctx.events.emit('nsec3map','skipped','DNSSEC not enabled'); write_summary(ctx,'not_dnssec'); return ctx
            n3=nsec3map_stage.run(ctx)
            if n3.get('zone_type')=='nsec':
                names=extract_nsec_names(ctx.workspace.root/'nsec3map/zone.txt', ctx.config.domain)
                (ctx.workspace.root/'reports/discovered_names.txt').write_text('\n'.join(names)+'\n')
                write_summary(ctx,'nsec'); return ctx
            if n3.get('zone_type')!='nsec3': write_summary(ctx,'unknown_nsec'); return ctx
            hashcatify.run(ctx); scheduler_stage.run(ctx); write_summary(ctx,'nsec3_scheduler'); return ctx
        except PipelineError as e:
            ctx.events.emit(e.stage,'failed',e.message,'error'); write_summary(ctx,'failed',e.stage,e.message); raise
