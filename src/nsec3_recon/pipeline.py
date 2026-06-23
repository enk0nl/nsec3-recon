from __future__ import annotations
from dataclasses import dataclass, field
import sys, time
from .config import PipelineConfig
from .workspace import Workspace
from .events import EventSink
from .report import write_summary
from .dependency_manifest import write_dependency_manifest
from .ui.console import ConsoleEventPrinter
from .ui.rich_dashboard import RichDashboard, resolve_dashboard_mode

class PipelineError(Exception):
    def __init__(self, stage, message): super().__init__(message); self.stage=stage; self.message=message

@dataclass
class PipelineContext:
    config: PipelineConfig; workspace: Workspace; events: EventSink; started_at: float=field(default_factory=time.time); state: dict=field(default_factory=dict); dashboard_controller: object|None=None; dashboard_mode: str='plain'

class Pipeline:
    def __init__(self, config:PipelineConfig): self.config=config.resolved(); self.ctx=None
    def _make_listeners(self, ws):
        mode=resolve_dashboard_mode(self.config.dashboard, stdout_isatty=sys.stdout.isatty())
        if mode == 'off': return [], None, mode
        if mode == 'plain':
            printer=ConsoleEventPrinter(verbose=self.config.verbose); return [printer.handle_event], None, mode
        try:
            dash=RichDashboard(self.config.domain, ws.root, refresh_per_second=self.config.dashboard_refresh_rate, scheduler_total_slices=self.config.total_slices, verbose=self.config.verbose); dash.start(); return [dash.handle_event], dash, mode
        except Exception as exc:
            if self.config.dashboard == 'rich':
                print(f"warning: Rich dashboard unavailable ({exc}); falling back to plain", file=sys.stderr)
            else:
                print(f"warning: Rich dashboard failed ({exc}); falling back to plain", file=sys.stderr)
            printer=ConsoleEventPrinter(verbose=self.config.verbose); return [printer.handle_event], None, 'plain'
    def setup(self):
        ws=Workspace.create(self.config.domain, self.config.out_dir)
        listeners,dashboard,mode=self._make_listeners(ws)
        if mode != 'rich':
            print(f"Workspace: {ws.root}", flush=True)
        ev=EventSink(ws.root/'events.jsonl', listeners=listeners)
        self.ctx=PipelineContext(self.config,ws,ev,dashboard_controller=dashboard,dashboard_mode=mode)
        write_dependency_manifest(self.ctx)
        ev.emit('preflight','workspace_created','workspace created', data={'workspace': str(ws.root)})
        return self.ctx
    def run(self):
        from .stages import preflight,dns_probe,axfr,nsec3map_stage,hashcatify,scheduler_stage
        from .adapters.scheduler import render_scheduler_config
        from .adapters.nsec3map import extract_nsec_names
        ctx=self.setup()
        try:
            preflight.run(ctx)
            render_scheduler_config(ctx.config.domain, ctx.config.assets_dir, ctx.workspace.root/'config/scheduler_config.json', ctx.config.scheduler_config or ctx.config.config_template, ctx.config.amass_bin, ctx.config.subfinder_bin, ctx.config.osint_enabled, ctx.config.hashcat_optimized_kernels, ctx.config.hashcat_optimized_kernel_failover)
            if ctx.config.dry_run:
                hf=ctx.workspace.root/'nsec3map/nsec3map_hashfile.hash'; sc=ctx.workspace.root/'config/scheduler_config.json'
                print('Planned commands:')
                print(f"Hashcat optimized kernels: {'enabled' if ctx.config.hashcat_optimized_kernels else 'disabled'}")
                print(f"Hashcat optimized-kernel failover: {'enabled' if ctx.config.hashcat_optimized_kernel_failover else 'disabled'}")
                print(f"nsec3map hashlimit: {ctx.config.nsec3map_hashlimit}")
                print(' '.join([ctx.config.nsec3map_python, 'map.py', '--detect-only', ctx.config.domain]))
                print(' '.join([ctx.config.nsec3map_python, 'map.py', f"--output={ctx.workspace.root/'nsec3map/zone.txt'}", f"--hashlimit={ctx.config.nsec3map_hashlimit}", ctx.config.domain]))
                print(' '.join([ctx.config.nsec3map_python, '<hashcatify.py>', str(ctx.workspace.root/'nsec3map/zone.txt'), str(hf)]))
                print(' '.join(ctx.config.scheduler_command(ctx.workspace.root,hf,sc)))
                write_summary(ctx,'dry_run'); return ctx
            dns_probe.run(ctx); ax=axfr.run(ctx)
            if ax.get('supported'):
                write_summary(ctx,'axfr'); return ctx
            detect = nsec3map_stage.detect(ctx)
            if detect.get('status') == 'not_dnssec' or detect.get('zone_type') == 'none':
                write_summary(ctx,'not_dnssec'); return ctx
            detected_zone_type = detect.get('zone_type') if detect.get('zone_type') in {'nsec','nsec3'} else None
            n3 = nsec3map_stage.enumerate(ctx, detected_zone_type=detected_zone_type)
            zone_type = detected_zone_type or n3.get('zone_type')
            ctx.state.setdefault('nsec3map', n3)['zone_type'] = zone_type
            if zone_type=='nsec':
                names=extract_nsec_names(ctx.workspace.root/'nsec3map/zone.txt', ctx.config.domain)
                (ctx.workspace.root/'reports/discovered_names.txt').write_text('\n'.join(names)+'\n')
                ctx.state['discovered_names']={'total':len(names),'by_source':{'nsec':len(names)}}
                ctx.events.emit('discovery','names_discovered', f'{len(names)} names discovered via NSEC walk', data={'source':'nsec','method':'nsec_walk','count':len(names),'names':names[-200:]})
                ctx.events.emit('nsec3map','nsec_names_extracted', f'extracted {len(names)} NSEC names', data={'zone_type': 'nsec'})
                write_summary(ctx,'nsec'); return ctx
            if zone_type!='nsec3':
                write_summary(ctx,'unknown_nsec'); return ctx
            hashcatify.run(ctx); scheduler_stage.run(ctx); write_summary(ctx,'nsec3_scheduler'); return ctx
        except PipelineError as e:
            ctx.events.emit(e.stage,'failed',e.message,'error'); write_summary(ctx,'failed',e.stage,e.message); raise
        finally:
            if ctx.dashboard_controller: ctx.dashboard_controller.stop()
