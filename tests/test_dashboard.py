from pathlib import Path
from nsec3_recon.config import PipelineConfig
from nsec3_recon.cli import build_parser
from nsec3_recon.ui.rich_dashboard import resolve_dashboard_mode, discover_potfile, RichDashboard
from nsec3_recon.ui.scheduler_parser import parse_scheduler_line
from nsec3_recon.ui.dashboard_state import DashboardState
from nsec3_recon.events import PipelineEvent


def test_cli_has_dashboard_option(capsys):
    p=build_parser(); text=p.format_help(); assert '--dashboard' in text
    for c in ('auto','rich','plain','off'): assert c in text

def test_cli_does_not_have_no_tui(): assert '--no-tui' not in build_parser().format_help()
def test_pipeline_config_dashboard_default_auto(): assert PipelineConfig('example.nl').dashboard == 'auto'
def test_resolve_dashboard_auto_tty_uses_rich(): assert resolve_dashboard_mode('auto', True, True) == 'rich'
def test_resolve_dashboard_auto_non_tty_uses_plain(): assert resolve_dashboard_mode('auto', False, True) == 'plain'
def test_resolve_dashboard_off_has_no_listener(): assert resolve_dashboard_mode('off', True, True) == 'off'

def test_scheduler_slice_parser_basic():
    r=parse_scheduler_line('[75/150] adaptive predictive-prefix reason=highest_score queue=4->0 written=4 enq=2 new=1 total=184877 reward=0.167 score=0.49->0.44 runtime=6.0s')
    d=r.data; assert r.parsed and d['slice_index']==75 and d['total_slices']==150 and d['schedule_name']=='adaptive' and d['arm']=='predictive-prefix'
    assert d['reason']=='highest_score' and d['queue_before']==4 and d['queue_after']==0 and d['written']==4 and d['enq']==2 and d['new']==1 and d['total']==184877
    assert d['reward']==0.167 and d['score_before']==0.49 and d['score_after']==0.44 and d['runtime_seconds']==6.0

def test_scheduler_slice_parser_extended_fields():
    r=parse_scheduler_line('[1/2] adaptive arm reason=x skip=3->1 progress=50% gate_queue=2/5 cooldown=1/4')
    d=r.data; assert d['skip_before']==3 and d['skip_after']==1 and d['progress']=='50%' and d['gate_queue_current']==2 and d['gate_queue_required']==5 and d['cooldown_current']==1 and d['cooldown_required']==4

def test_scheduler_slice_parser_nonmatching_line():
    r=parse_scheduler_line('hello scheduler'); assert not r.parsed and r.data['message']=='hello scheduler'

def test_dashboard_state_updates_on_stage_events():
    s=DashboardState('example.nl')
    s.handle_event(PipelineEvent('now','dns_probe','info','started','DNS probe started',{})); assert s.stages['dns_probe'].status=='running'
    s.handle_event(PipelineEvent('now','dns_probe','info','completed','DNS probe completed',{'probe_status':'ok'})); assert s.stages['dns_probe'].status=='completed'
    s.handle_event(PipelineEvent('now','axfr','error','failed','boom',{})); assert s.stages['axfr'].status=='failed'

def test_dashboard_state_updates_current_and_previous_slice():
    s=DashboardState(); s.update_slice({'slice_index':1,'arm':'a'}); s.update_slice({'slice_index':2,'arm':'b'}); assert s.previous_slice['slice_index']==1 and s.current_slice['slice_index']==2

def test_dashboard_arm_stats_aggregate():
    s=DashboardState(); s.update_slice({'slice_index':1,'arm':'a','new':2,'reward':1.0,'runtime_seconds':2.0,'score_after':0.4}); s.update_slice({'slice_index':2,'arm':'a','new':3,'reward':2.0,'runtime_seconds':4.0,'score_after':0.6})
    a=s.arm_stats['a']; assert a.run_count==2 and a.total_new==5 and a.avg_reward==1.5 and a.avg_runtime==3.0 and a.last_score==0.6

def test_nsec3_potfile_names_are_discovered_names(tmp_path):
    p=tmp_path/'x.pot'; p.write_text('h:cand\n')
    d=RichDashboard('example.nl', tmp_path); d.state.current_potfile_path=str(p); d.poll_external_sources(); d.poll_external_sources()
    assert d.state.discovered_names_count==1 and d.state.discovered_names_recent[0].name=='cand' and d.state.discovered_names_recent[0].source=='nsec3'

def test_dashboard_potfile_discovery(tmp_path):
    p=tmp_path/'scheduler'/'run.pot'; p.parent.mkdir(); p.write_text('')
    assert discover_potfile(tmp_path)==p

def test_recent_activity_keeps_unparsed_scheduler_messages():
    d=RichDashboard('example.nl')
    d.handle_event(PipelineEvent('now','scheduler','info','stdout','unparsed line',{}))
    assert any('unparsed line' in a['message'] for a in d.state.recent_activity)

def test_scheduler_stdout_events_are_not_printed_raw_in_rich_mode(capsys):
    d=RichDashboard('example.nl')
    d.handle_event(PipelineEvent('now','scheduler','info','stdout','[1/2] adaptive a new=1',{}))
    assert capsys.readouterr().out == '' and d.state.current_slice is None
    assert d.state.latest_stdout_slice_debug['slice_index'] == 1

def test_slice_panel_labels_are_completed_slice_labels():
    s=DashboardState('example.nl','/tmp/ws'); s.scheduler_started=True
    import pytest
    Console=pytest.importorskip('rich.console').Console
    console=Console(record=True, width=160, color_system=None); console.print(__import__('nsec3_recon.ui.widgets', fromlist=['build_dashboard']).build_dashboard(s))
    out=console.export_text()
    for h in ('Pipeline','Last completed slice','Previous completed slice','Arm statistics','Discovered names','Recent activity'): assert h in out
    assert 'Current slice' not in out

def test_console_mode_still_works(tmp_path):
    from nsec3_recon.pipeline import Pipeline
    ctx=Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r', dashboard='plain')).setup()
    assert ctx.dashboard_mode=='plain' and len(ctx.events.listeners)==1

def test_off_mode_suppresses_live_events(tmp_path):
    from nsec3_recon.pipeline import Pipeline
    ctx=Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r', dashboard='off')).setup()
    assert ctx.dashboard_mode=='off' and ctx.events.listeners==[] and (ctx.workspace.root/'events.jsonl').exists()

def test_ui_failure_falls_back_in_auto_mode(monkeypatch,tmp_path):
    import nsec3_recon.pipeline as pp
    class Bad:
        def __init__(self,*a,**k): raise RuntimeError('bad ui')
    monkeypatch.setattr(pp, 'RichDashboard', Bad)
    monkeypatch.setattr(pp.sys.stdout, 'isatty', lambda: True)
    ctx=pp.Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r', dashboard='auto')).setup()
    assert ctx.dashboard_mode=='plain' and (ctx.workspace.root/'events.jsonl').exists()

def test_scheduler_slice_state_uses_last_completed_names():
    s=DashboardState(); s.update_slice({'slice_index':10,'arm':'a'}); s.update_slice({'slice_index':11,'arm':'b'})
    assert s.last_completed_slice['slice_index']==11 and s.previous_completed_slice['slice_index']==10

def test_parsed_scheduler_lines_do_not_go_to_recent_activity():
    d=RichDashboard('example.nl')
    raw='[75/150] adaptive predictive-prefix reason=highest_score queue=4->0 written=4 enq=2 new=1 total=184877 reward=0.167 score=0.49->0.44 runtime=6.0s'
    d.handle_event(PipelineEvent('now','scheduler','info','stdout',raw,{}))
    assert d.state.last_completed_slice is None
    assert d.state.latest_stdout_slice_debug['slice_index'] == 75
    assert not any(raw in a['message'] for a in d.state.recent_activity)

def test_rich_mode_does_not_use_console_printer(monkeypatch,tmp_path):
    import nsec3_recon.pipeline as pp
    class FakeDashboard:
        def __init__(self,*a,**k): self.state=DashboardState()
        def start(self): pass
        def handle_event(self,event): pass
    monkeypatch.setattr(pp, 'resolve_dashboard_mode', lambda *a, **k: 'rich')
    monkeypatch.setattr(pp, 'RichDashboard', FakeDashboard)
    ctx=pp.Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r', dashboard='rich')).setup()
    assert ctx.dashboard_mode=='rich' and len(ctx.events.listeners)==1
    assert ctx.events.listeners[0].__self__.__class__.__name__ == 'FakeDashboard'

def test_live_settings_reduce_flicker(monkeypatch):
    import sys, types
    calls={}
    rich_mod=types.ModuleType('rich'); live_mod=types.ModuleType('rich.live')
    class FakeLive:
        def __init__(self, renderable, **kwargs): calls.update(kwargs)
        def start(self): pass
        def update(self, *args, **kwargs): pass
        def stop(self): pass
    live_mod.Live=FakeLive
    monkeypatch.setitem(sys.modules, 'rich', rich_mod); monkeypatch.setitem(sys.modules, 'rich.live', live_mod)
    monkeypatch.setattr(RichDashboard, 'render', lambda self: 'render')
    d=RichDashboard(refresh_per_second=2); d.start(); d.stop()
    assert calls['transient'] is False and calls['screen'] is False and calls['refresh_per_second'] <= 2 and calls['auto_refresh'] is False

def test_final_summary_prints_discovered_names(monkeypatch, capsys):
    from nsec3_recon import cli
    class Ctx:
        class Workspace:
            class Root:
                def __truediv__(self, other): return '/tmp/summary.json'
            root=Root()
        workspace=Workspace(); state={'summary': {'completed_via': 'nsec3_scheduler'}}
        class Dash:
            class State: discovered_names_count=1234
            state=State()
        dashboard_controller=Dash()
    monkeypatch.setattr(cli, 'Pipeline', lambda cfg: type('P', (), {'run': lambda self: Ctx()})())
    assert cli.main(['example.nl','--dashboard','rich']) == 0
    out=capsys.readouterr().out
    assert 'Completed via:' in out and 'Summary:' in out and 'Discovered names: 1234' in out

def _render_text(state):
    import pytest
    Console=pytest.importorskip('rich.console').Console
    console=Console(record=True, width=180, height=45, color_system=None)
    console.print(__import__('nsec3_recon.ui.widgets', fromlist=['build_dashboard']).build_dashboard(state))
    return console.export_text()

def test_dashboard_render_contains_key_sections():
    s=DashboardState('example.nl','/tmp/ws'); s.scheduler_started=True
    out=_render_text(s)
    for h in ('Pipeline','Last completed slice','Previous completed slice','Arm statistics','Discovered names','Recent activity'): assert h in out

def test_arm_stats_headers_are_readable():
    s=DashboardState('example.nl','/tmp/ws'); s.update_slice({'slice_index':1,'arm':'feedback/predictive-prefix','new':1,'reward':1.2,'runtime_seconds':3.4})
    out=_render_text(s)
    for h in ('Arm','Runs','Total','Last','R','Score','Avg t','Seen'): assert h in out
    assert 'Avg R' not in out
    for bad in ('to...','avg_...','las...'): assert bad not in out

def test_arm_stats_numeric_formatting():
    s=DashboardState('example.nl','/tmp/ws'); s.update_slice({'slice_index':1,'arm':'a','new':1,'reward':1.234,'runtime_seconds':3.45})
    out=_render_text(s)
    assert '1.23' in out and '3.5s' in out

def test_arm_stats_limits_rows_and_reports_more():
    s=DashboardState('example.nl','/tmp/ws')
    for i in range(12): s.update_slice({'slice_index':i+1,'arm':f'arm-{i}','new':i,'reward':float(i),'runtime_seconds':1.0})
    out=_render_text(s)
    assert '+4 more arms' in out

def test_discovered_names_have_timestamps():
    s=DashboardState('example.nl','/tmp/ws'); s.current_potfile_path='/tmp/ws/scheduler/run.pot'; s.add_discovered_names(['api'], source='nsec3', method='hashcat_potfile')
    out=_render_text(s)
    import re
    assert re.search(r'\d{2}:\d{2}:\d{2}\s+api', out)
    assert not re.search(r'\d{2}:\d{2}:\d{2}\s+nsec3\s+api', out)

def test_discovered_names_panel_prominent():
    s=DashboardState('example.nl','/tmp/ws')
    out=_render_text(s)
    assert 'Discovered names' in out and 'total=0' in out

def test_discovered_names_render_timestamp_spacing():
    s=DashboardState('example.nl','/tmp/ws')
    from nsec3_recon.ui.dashboard_state import DiscoveredName
    s.discovered_names_recent.append(DiscoveredName(name='www', source='nsec3', method='hashcat_potfile', first_seen_at='21:07:22'))
    s.discovered_names_count=1
    out=_render_text(s)
    assert '21:07:22  www' in out
    assert '21:07:22www' not in out

def test_dashboard_refresh_rate_default_is_low():
    assert PipelineConfig('example.nl').dashboard_refresh_rate <= 2.0
    assert RichDashboard().refresh_per_second <= 2.0

def test_dashboard_refresh_rate_cli_option():
    from nsec3_recon.cli import build_parser
    args=build_parser().parse_args(['example.nl','--dashboard-refresh-rate','1'])
    assert args.dashboard_refresh_rate == 1.0

def test_dashboard_refresh_rate_clamped_or_validated():
    import pytest
    with pytest.raises(ValueError):
        PipelineConfig('example.nl', dashboard_refresh_rate=0).resolved()
    assert PipelineConfig('example.nl', dashboard_refresh_rate=999).resolved().dashboard_refresh_rate == 10.0

def test_rich_dashboard_does_not_refresh_on_every_event():
    class FakeLive:
        def __init__(self): self.calls=0
        def update(self, *a, **k): self.calls += 1
    d=RichDashboard('example.nl')
    d._live=FakeLive()
    for i in range(5):
        d.handle_event(PipelineEvent('now','scheduler','info','stdout',f'[1/2] adaptive arm new={i}',{}))
    assert d._live.calls == 0
    assert d._dirty is True

def test_live_constructed_with_non_transient_non_screen(monkeypatch):
    import sys, types
    calls={}
    rich_mod=types.ModuleType('rich'); live_mod=types.ModuleType('rich.live')
    class FakeLive:
        def __init__(self, renderable, **kwargs): calls.update(kwargs)
        def start(self): pass
        def update(self, *args, **kwargs): pass
        def stop(self): pass
    live_mod.Live=FakeLive
    monkeypatch.setitem(sys.modules, 'rich', rich_mod); monkeypatch.setitem(sys.modules, 'rich.live', live_mod)
    monkeypatch.setattr(RichDashboard, 'render', lambda self: 'render')
    d=RichDashboard(refresh_per_second=2); d.start(); d.stop()
    assert calls['transient'] is False and calls['screen'] is False and calls['refresh_per_second'] == 2
    assert calls['auto_refresh'] is False

def test_dashboard_panel_renamed_to_discovered_names():
    s=DashboardState('example.nl','/tmp/ws')
    out=_render_text(s)
    assert 'Discovered names' in out
    assert 'Recovered candidates' not in out

def test_discovered_name_record_dedupes_normalized_names():
    s=DashboardState('example.nl')
    s.add_discovered_names(['www.example.nl.', 'WWW.example.nl'], source='axfr', method='zone_transfer')
    assert s.discovered_names_count == 1
    assert len(s.discovered_names_recent) == 1

def test_discovered_names_batch_count():
    s=DashboardState('example.nl')
    s.handle_event(PipelineEvent('now','discovery','info','names_discovered','names discovered',{'source':'nsec','method':'nsec_walk','count':1000,'names':[f'n{i}.example.nl' for i in range(20)]}))
    assert s.discovered_names_count == 1000
    assert s.discovered_names_by_source['nsec'] == 1000

def test_plain_console_summarizes_discovery_batch(capsys):
    from nsec3_recon.ui.console import ConsoleEventPrinter
    printer=ConsoleEventPrinter(verbose=False)
    printer.handle_event(PipelineEvent('now','discovery','info','names_discovered','1000 names discovered via AXFR',{'source':'axfr','method':'zone_transfer','count':1000,'names':['a','b','c']}))
    out=capsys.readouterr().out
    assert 'names discovered' in out and "['a'" not in out and "'b'" not in out and "'c'" not in out

def test_arm_stats_headers_use_reward_and_score():
    s=DashboardState('example.nl','/tmp/ws'); s.update_slice({'slice_index':1,'arm':'feedback/predictive-prefix','new':1,'reward':4.747,'runtime_seconds':3.4,'score_after':0.73})
    out=_render_text(s)
    for h in ('Arm','Runs','Total','Last','R','Score','Avg t','Seen'): assert h in out
    assert 'Avg R' not in out

def test_arm_stats_score_uses_score_after():
    s=DashboardState('example.nl','/tmp/ws')
    s.update_slice({'source':'jobs_jsonl','slice_index':1,'arm':'arm','reward':4.747,'score_before':0.02,'score_after':0.73,'runtime_seconds':2.0})
    a=s.arm_stats['arm']
    assert a.last_reward == 4.747 and a.last_score == 0.73
    out=_render_text(s)
    assert '4.75' in out and '0.73' in out

def test_arm_stats_score_missing_displays_dash():
    s=DashboardState('example.nl','/tmp/ws'); s.update_slice({'slice_index':1,'arm':'arm','reward':1.0})
    out=_render_text(s)
    assert '–' in out

def test_axfr_success_populates_discovered_names_event(monkeypatch,tmp_path):
    from nsec3_recon.stages import axfr
    from nsec3_recon.pipeline import PipelineContext
    from nsec3_recon.config import PipelineConfig
    from nsec3_recon.workspace import Workspace
    from nsec3_recon.events import EventSink
    monkeypatch.setattr(axfr.dns, 'try_axfr', lambda domain, ns: 'www.example.nl. 3600 IN A 192.0.2.1\napi.example.nl. 3600 IN A 192.0.2.2\n')
    events=[]; ws=Workspace.create('example.nl', tmp_path/'r'); ev=EventSink(ws.root/'events.jsonl', listeners=[events.append])
    ctx=PipelineContext(PipelineConfig('example.nl', out_dir=tmp_path/'r', dashboard='off'), ws, ev); ctx.state['nameservers']=[{'name':'ns1.example.nl','addresses':['192.0.2.53']}]
    axfr.run(ctx)
    discovery=[e for e in events if e.stage=='discovery' and e.event=='names_discovered']
    assert discovery and discovery[0].data['source']=='axfr' and discovery[0].data['count']==2

def test_nsec_path_populates_discovered_names_event(monkeypatch,tmp_path):
    from nsec3_recon.pipeline import Pipeline
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    from nsec3_recon.adapters import nsec3map as nsec3_adapter
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled':True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: ctx.state.update(nsec3map_detect={'status':'success','zone_type':'nsec'}) or ctx.state['nsec3map_detect'])
    def enum(ctx, detected_zone_type=None):
        (ctx.workspace.root/'nsec3map').mkdir(exist_ok=True)
        (ctx.workspace.root/'nsec3map/zone.txt').write_text('')
        ctx.state['nsec3map']={'zone_type':'nsec','zone_file':'nsec3map/zone.txt'}; return ctx.state['nsec3map']
    monkeypatch.setattr(nsec3map_stage,'enumerate',enum)
    monkeypatch.setattr(nsec3_adapter,'extract_nsec_names',lambda path, domain:['www.example.nl','api.example.nl'])
    ctx=Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r', dashboard='off')).run()
    lines=(ctx.workspace.root/'events.jsonl').read_text()
    assert '"stage": "discovery"' in lines and '"source": "nsec"' in lines

def test_summary_includes_discovered_names_counts(tmp_path):
    from nsec3_recon.pipeline import PipelineContext
    from nsec3_recon.config import PipelineConfig
    from nsec3_recon.workspace import Workspace
    from nsec3_recon.events import EventSink
    from nsec3_recon.report import write_summary
    import json
    ws=Workspace.create('example.nl', tmp_path/'r'); ctx=PipelineContext(PipelineConfig('example.nl', out_dir=tmp_path/'r'), ws, EventSink(ws.root/'events.jsonl'))
    ctx.state['discovered_names']={'total':3,'by_source':{'axfr':3}}
    write_summary(ctx, 'axfr')
    data=json.loads((ws.root/'reports/summary.json').read_text())
    assert data['discovered_names']['total']==3 and data['discovered_names']['by_source']['axfr']==3

def test_arm_table_header_uses_total_not_new():
    s=DashboardState('example.nl','/tmp/ws'); s.update_slice({'slice_index':1,'arm':'arm-a','new':3,'reward':1.0,'score_after':0.2})
    out=_render_text(s)
    assert 'Total' in out
    assert ' New ' not in out

def test_arm_total_is_sum_of_slice_new():
    s=DashboardState('example.nl','/tmp/ws')
    for data in (
        {'source':'jobs_jsonl','slice_index':1,'arm':'arm-a','new':3,'total':10,'reward':1.0,'score_after':0.2,'runtime_seconds':1.0},
        {'source':'jobs_jsonl','slice_index':2,'arm':'arm-a','new':5,'total':15,'reward':2.0,'score_after':0.3,'runtime_seconds':1.0},
    ):
        s.update_slice(data)
    arm=s.arm_stats['arm-a']
    assert arm.total_new == 8 and arm.last_new == 5
    out=_render_text(s)
    assert '8' in out and '5' in out

def test_arm_total_does_not_use_global_total_field():
    s=DashboardState('example.nl','/tmp/ws')
    s.update_slice({'source':'jobs_jsonl','slice_index':1,'arm':'arm-a','new':3,'total':999,'reward':1.0,'score_after':0.2})
    assert s.arm_stats['arm-a'].total_new == 3
    assert s.arm_stats['arm-a'].total_new != 999

def test_arm_last_new_is_latest_slice_new():
    s=DashboardState('example.nl','/tmp/ws')
    for i, new in enumerate((3,0,7), start=1):
        s.update_slice({'slice_index':i,'arm':'arm-a','new':new})
    assert s.arm_stats['arm-a'].total_new == 10
    assert s.arm_stats['arm-a'].last_new == 7

def test_arm_stats_include_warmup_records_from_jobs_jsonl():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws')
    for record in (
        {'phase':'warmup','arm':'dict/seclists','new':10,'reward':1.0,'score_after':0.5,'runtime_seconds':5},
        {'phase':'adaptive','arm':'dict/seclists','new':3,'reward':0.3,'score_after':0.4,'runtime_seconds':5},
    ):
        s.update_slice(normalize_scheduler_record(record).data)
    arm=s.arm_stats['dict/seclists']
    assert arm.run_count == 2 and arm.total_new == 13 and arm.last_new == 3 and arm.last_score == 0.4

def test_arm_stats_do_not_exclude_phase_warmup():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws')
    s.update_slice(normalize_scheduler_record({'phase':'warmup','arm':'dict/a','new':2,'runtime_seconds':1}).data)
    assert s.arm_stats['dict/a'].total_new == 2

def test_jobs_jsonl_global_total_not_used_as_arm_total():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws')
    s.update_slice(normalize_scheduler_record({'phase':'warmup','arm':'dict/a','new':2,'total':999}).data)
    assert s.arm_stats['dict/a'].total_new == 2

def test_last_previous_completed_slice_include_warmup():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws')
    s.update_slice(normalize_scheduler_record({'phase':'warmup','slice':1,'arm':'dict/a','new':2}).data)
    s.update_slice(normalize_scheduler_record({'phase':'warmup','slice':2,'arm':'dict/b','new':3}).data)
    assert s.previous_completed_slice['phase'] == 'warmup' and s.last_completed_slice['phase'] == 'warmup'

def test_jobs_jsonl_tail_processes_new_records_once(tmp_path):
    import json
    p=tmp_path/'scheduler'/'jobs.jsonl'; p.parent.mkdir()
    p.write_text(json.dumps({'phase':'warmup','slice':1,'arm':'dict/a','new':2})+'\n')
    d=RichDashboard('example.nl', tmp_path, potfile_poll_interval_seconds=0)
    d.poll_external_sources(); d.poll_external_sources()
    assert d.state.arm_stats['dict/a'].total_new == 2
    with p.open('a') as f: f.write(json.dumps({'phase':'warmup','slice':2,'arm':'dict/a','new':3})+'\n')
    d.poll_external_sources()
    assert d.state.arm_stats['dict/a'].total_new == 5

def test_stdout_and_jobs_jsonl_do_not_double_count_same_slice(tmp_path):
    import json
    d=RichDashboard('example.nl', tmp_path, potfile_poll_interval_seconds=0)
    raw='[1/150] adaptive arm-a reason=x new=3 total=10 reward=1.0 score=0.1->0.2 runtime=1.0s'
    d.handle_event(PipelineEvent('now','scheduler','info','stdout',raw,{}))
    p=tmp_path/'scheduler'/'jobs.jsonl'; p.parent.mkdir()
    p.write_text(json.dumps({'phase':'adaptive','slice':1,'arm':'arm-a','new':3,'total':10,'reward':1.0,'score_after':0.2,'runtime_seconds':1.0})+'\n')
    d.poll_external_sources()
    assert d.state.arm_stats['arm-a'].total_new == 3

def test_jobs_jsonl_record_normalizer_tolerates_field_variants():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    a=normalize_scheduler_record({'phase':'warmup','arm_name':'a','new_discoveries':4,'runtime':2,'score':0.7}).data
    b=normalize_scheduler_record({'warmup':True,'arm':'b','discoveries':5,'actual_runtime_seconds':3,'score_after':0.8}).data
    assert a['arm']=='a' and a['new']==4 and a['runtime_seconds']==2 and a['score_after']==0.7
    assert b['phase']=='warmup' and b['new']==5 and b['runtime_seconds']==3 and b['score_after']==0.8

def test_discovered_names_renderer_shows_name_not_source():
    from nsec3_recon.ui.dashboard_state import DiscoveredName
    s=DashboardState('example.nl','/tmp/ws')
    s.discovered_names_recent.append(DiscoveredName(name='loting', source='nsec3', method='hashcat_potfile', first_seen_at='07:12:02'))
    s.discovered_names_count=1; s.discovered_names_by_source={'nsec3':1}
    out=_render_text(s)
    assert '07:12:02  loting' in out
    assert '07:12:02  nsec3' not in out

def test_discovered_names_no_source_column_by_default():
    s=DashboardState('example.nl','/tmp/ws'); s.add_discovered_names(['loting'], source='nsec3')
    out=_render_text(s)
    assert 'source' not in out.split('Discovered names', 1)[1].split('total=', 1)[0].lower()

def test_discovered_names_footer_summarizes_source():
    s=DashboardState('example.nl','/tmp/ws'); s.current_potfile_path='/tmp/ws/scheduler/run.pot'; s.add_discovered_names(['loting'], source='nsec3')
    assert 'source: nsec3' in _render_text(s)

def test_discovered_names_mixed_source_footer():
    s=DashboardState('example.nl','/tmp/ws'); s.add_discovered_names(['a'], source='axfr'); s.add_discovered_names(['b'], source='nsec3')
    out=_render_text(s)
    assert 'source: axfr,nsec3' in out

def test_discovered_name_column_has_width():
    long='very-long-discovered-name-that-should-remain-visible.example.nl'
    s=DashboardState('example.nl','/tmp/ws'); s.add_discovered_names([long], source='nsec3')
    out=_render_text(s)
    assert 'very-long-discovered-name' in out

def _real_warmup_record():
    return {
        'timestamp':'2026-06-23T07:25:00.444130+00:00','job_id':1,'phase':'warmup','arm':'dict/seclists',
        'arm_family':'dict','arm_short_name':'seclists','arm_type':'dictionary','attack_type':'dictionary',
        'selection_reason':'warmup','requested_slice_seconds':15,'runtime_seconds':18.737359523773193,
        'exit_code':4,'exit_meaning':'runtime_reached','execution_status':'executed','valid_work':True,
        'new_cracks':105,'marginal_new_cracks':105,'shared_new_cracks':105,
        'warmup_scoring':'arm_local','potfile_scope':'arm_local','arm_local_cracks':105,'arm_local_new_cracks':105,
        'reward_used_for_score':5.603777835760706,'total_cracks':105,'reward':5.603777835760706,
        'score_before':0.0,'score_after':0.8405666753641059,'exhausted':False,
    }

def test_jobs_jsonl_normalizer_reads_real_warmup_schema():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    d=normalize_scheduler_record(_real_warmup_record()).data
    assert d['record_key']=='job:1' and d['phase']=='warmup' and d['arm']=='dict/seclists' and d['reason']=='warmup'
    assert d['new']==105 and d['global_total']==105 and d['reward']==5.603777835760706
    assert d['score_before']==0.0 and d['score_after']==0.8405666753641059 and d['runtime_seconds']==18.737359523773193

def test_arm_stats_include_warmup_shared_new_cracks():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws'); s.update_slice(normalize_scheduler_record(_real_warmup_record()).data)
    arm=s.arm_stats['dict/seclists']
    assert arm.run_count==1 and arm.total_new==105 and arm.last_new==105
    assert arm.last_reward==5.603777835760706 and arm.last_score==0.8405666753641059 and round(arm.avg_runtime,1)==18.7
    assert arm.last_seen_slice == 1

def test_new_field_precedence_prefers_shared_new_cracks():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    d=normalize_scheduler_record({'arm':'a','shared_new_cracks':10,'marginal_new_cracks':20,'new_cracks':30,'new':40}).data
    assert d['new'] == 10

def test_new_field_fallback_to_new_cracks():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    assert normalize_scheduler_record({'arm':'a','new_cracks':30}).data['new'] == 30

def test_reward_precedence_prefers_reward_used_for_score():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    assert normalize_scheduler_record({'arm':'a','new':1,'reward_used_for_score':5.0,'reward':2.0}).data['reward'] == 5.0

def test_seen_uses_job_id_when_slice_missing():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws'); s.update_slice(normalize_scheduler_record({'job_id':7,'arm':'a','new':1}).data)
    assert s.arm_stats['a'].last_seen_slice == 7

def test_invalid_non_work_job_record_ignored():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    assert normalize_scheduler_record({'event':'startup','new':1}) is None
    assert normalize_scheduler_record({'arm':'a','event':'metadata'}) is None

def test_valid_work_false_ignored():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    assert normalize_scheduler_record({'valid_work':False,'arm':'dict/seclists','shared_new_cracks':10}) is None

def test_jobs_jsonl_tail_updates_arm_table(tmp_path):
    import json
    p=tmp_path/'scheduler'/'jobs.jsonl'; p.parent.mkdir(); p.write_text(json.dumps(_real_warmup_record())+'\n')
    d=RichDashboard('example.nl', tmp_path, potfile_poll_interval_seconds=0); d.poll_external_sources()
    assert d.state.arm_stats['dict/seclists'].total_new == 105

def test_potfile_discovery_source_is_nsec3(tmp_path):
    p=tmp_path/'run.pot'; p.write_text('h:loting\n')
    d=RichDashboard('example.nl', tmp_path); d.state.current_potfile_path=str(p); d.poll_external_sources()
    item=d.state.discovered_names_recent[0]
    assert item.source=='nsec3' and item.method=='hashcat_potfile'

def test_discovered_names_footer_uses_nsec3_not_run_pot():
    s=DashboardState('example.nl','/tmp/ws'); s.current_potfile_path='/tmp/ws/scheduler/run.pot'; s.add_discovered_names(['loting'], source='nsec3')
    out=_render_text(s)
    assert 'source: nsec3' in out
    assert 'source: run.pot' not in out

def test_run_pot_may_be_artifact_source_not_logical_source():
    from nsec3_recon.ui.dashboard_state import DiscoveredName
    item=DiscoveredName(name='loting', source='nsec3', method='hashcat_potfile', first_seen_at='07:12:02')
    item.source_file='run.pot'
    s=DashboardState('example.nl','/tmp/ws'); s.discovered_names_recent.append(item); s.discovered_names_by_source={'nsec3':1}; s.discovered_names_count=1
    out=_render_text(s)
    assert 'source: nsec3' in out and 'source: run.pot' not in out

def test_axfr_nsec_nsec3_source_labels():
    s=DashboardState('example.nl')
    s.add_discovered_names(['a'], source='axfr'); s.add_discovered_names(['b'], source='nsec'); s.add_discovered_names(['c'], source='nsec3')
    assert set(s.discovered_names_by_source) == {'axfr','nsec','nsec3'}

def test_discovered_names_rows_show_name_only():
    from nsec3_recon.ui.dashboard_state import DiscoveredName
    s=DashboardState('example.nl','/tmp/ws'); s.discovered_names_recent.append(DiscoveredName(name='loting', source='nsec3', method='hashcat_potfile', first_seen_at='07:12:02')); s.discovered_names_count=1; s.discovered_names_by_source={'nsec3':1}
    out=_render_text(s)
    assert '07:12:02  loting' in out and '07:12:02  nsec3  loting' not in out

def test_slice_total_falls_back_to_config_total_slices():
    s=DashboardState('example.nl','/tmp/ws', scheduler_total_slices=150)
    s.update_slice({'source':'jobs_jsonl','job_id':18,'slice_index':18,'arm':'a','new':1})
    out=_render_text(s)
    assert '18/150' in out and '18/None' not in out

def test_slice_total_unknown_renders_question_mark_only_without_config():
    s=DashboardState('example.nl','/tmp/ws')
    s.update_slice({'source':'jobs_jsonl','job_id':18,'slice_index':18,'arm':'a','new':1})
    assert '18/?' in _render_text(s)

def test_last_previous_slices_are_not_same_record():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record, parse_scheduler_line
    s=DashboardState('example.nl','/tmp/ws', scheduler_total_slices=150)
    s.update_slice(parse_scheduler_line('[18/150] adaptive arm-a reason=x new=3 total=218 reward=1.0 score=0.1->0.2 runtime=1.0s').data)
    s.update_slice(normalize_scheduler_record({'job_id':18,'phase':'adaptive','arm':'arm-a','shared_new_cracks':3,'total_cracks':218,'reward_used_for_score':1.0,'score_after':0.2,'runtime_seconds':1.0}).data)
    assert s.last_completed_slice['slice_index'] == 18
    assert s.previous_completed_slice is None or s.previous_completed_slice['slice_index'] != 18

def test_jobs_record_updates_existing_stdout_slice_without_shifting():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record, parse_scheduler_line
    s=DashboardState('example.nl','/tmp/ws', scheduler_total_slices=150)
    s.update_slice(parse_scheduler_line('[18/150] adaptive arm-a reason=x new=3 total=218 reward=1.0 score=0.1->0.2 runtime=1.0s').data)
    s.update_slice(normalize_scheduler_record({'job_id':18,'phase':'adaptive','arm':'arm-a','shared_new_cracks':3,'total_cracks':218,'reward_used_for_score':1.0,'score_after':0.2,'runtime_seconds':1.0}).data)
    assert len(s.completed_slice_order) == 1
    assert s.last_completed_slice['source'] == 'jobs_jsonl'
    assert s.previous_completed_slice is None

def test_two_unique_jobs_populate_last_and_previous():
    s=DashboardState('example.nl','/tmp/ws', scheduler_total_slices=150)
    s.update_slice({'source':'jobs_jsonl','job_id':17,'slice_index':17,'arm':'a','new':1})
    s.update_slice({'source':'jobs_jsonl','job_id':18,'slice_index':18,'arm':'b','new':1})
    assert s.previous_completed_slice['slice_index'] == 17 and s.last_completed_slice['slice_index'] == 18

def test_jobs_jsonl_job_id_used_as_seen_index_and_rendered_index():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws', scheduler_total_slices=150)
    s.update_slice(normalize_scheduler_record({'job_id':18,'phase':'warmup','arm':'a','shared_new_cracks':1}).data)
    assert s.arm_stats['a'].last_seen_slice == 18
    out=_render_text(s)
    assert 'job 18/150' in out and '18/None' not in out

def test_hashcatify_completed_sets_nsec3_hash_total():
    s=DashboardState('example.nl')
    s.handle_event(PipelineEvent('now','hashcatify','info','completed','done',{'hash_count':123456}))
    assert s.nsec3_hash_total == 123456

def test_jobs_total_cracks_updates_nsec3_hash_cracked():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl')
    s.update_slice(normalize_scheduler_record({'job_id':1,'arm':'a','shared_new_cracks':1,'total_cracks':218}).data)
    assert s.nsec3_hash_cracked == 218

def test_nsec3_progress_percent():
    s=DashboardState('example.nl'); s.nsec3_hash_total=123456; s.nsec3_hash_cracked=218
    assert round(s.nsec3_hash_progress_percent, 4) == 0.1766
    assert '0.18%' in _render_text(s)

def test_nsec3_progress_uses_hashes_not_unique_names():
    s=DashboardState('example.nl'); s.nsec3_hash_total=123456; s.nsec3_hash_cracked=218; s.discovered_names_count=102
    assert s.nsec3_hash_progress_percent == 100 * 218 / 123456

def test_nsec3_progress_render_contains_hashes_and_names():
    s=DashboardState('example.nl','/tmp/ws'); s.nsec3_hash_total=123456; s.nsec3_hash_cracked=218; s.discovered_names_count=102
    out=_render_text(s)
    assert 'hashes=218/123456' in out and 'names=102' in out

def test_total_field_not_used_as_total_slices():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws', scheduler_total_slices=150)
    s.update_slice(normalize_scheduler_record({'job_id':18,'arm':'a','shared_new_cracks':1,'total_cracks':218}).data)
    out=_render_text(s)
    assert '18/150' in out and '18/218' not in out

def test_global_total_rendered_as_total_cracks():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws', scheduler_total_slices=150)
    s.update_slice(normalize_scheduler_record({'job_id':18,'phase':'adaptive','arm':'a','shared_new_cracks':6,'total_cracks':218}).data)
    out=_render_text(s)
    assert '18/150' in out and 'total=218' in out

def test_scheduler_stdout_slice_does_not_update_completed_slices():
    from nsec3_recon.events import PipelineEvent
    d=RichDashboard('example.nl')
    d.handle_event(PipelineEvent('now','scheduler','info','stdout','[4/150] warmup dict/opentaal_dutch reason=warmup new=2 total=137 reward=11.20 runtime=2.9s',{}))
    assert d.state.last_completed_slice is None
    assert d.state.previous_completed_slice is None
    assert d.state.latest_stdout_slice_debug['slice_index'] == 4


def test_scheduler_stdout_slice_does_not_update_arm_stats():
    from nsec3_recon.events import PipelineEvent
    d=RichDashboard('example.nl')
    d.handle_event(PipelineEvent('now','scheduler','info','stdout','[4/150] warmup dict/opentaal_dutch reason=warmup new=2 total=137 reward=11.20 runtime=2.9s',{}))
    assert d.state.arm_stats == {}


def test_jobs_jsonl_record_updates_completed_slices():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws', scheduler_total_slices=150)
    assert s.update_scheduler_job(normalize_scheduler_record({'job_id':4,'phase':'warmup','arm':'dict/opentaal_dutch','shared_new_cracks':2,'total_cracks':137,'reward_used_for_score':11.2,'score_after':0.5,'runtime_seconds':2.9}).data)
    assert s.last_completed_slice['job_id'] == 4
    assert s.previous_completed_slice is None
    assert s.arm_stats['dict/opentaal_dutch'].total_new == 2


def test_stdout_then_jobs_does_not_duplicate_last_previous():
    from nsec3_recon.events import PipelineEvent
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    d=RichDashboard('example.nl','/tmp/ws', scheduler_total_slices=150)
    d.handle_event(PipelineEvent('now','scheduler','info','stdout','[4/150] warmup dict/opentaal_dutch reason=warmup new=2 total=137 reward=11.20 runtime=2.9s',{}))
    d.state.update_scheduler_job(normalize_scheduler_record({'job_id':4,'phase':'warmup','arm':'dict/opentaal_dutch','shared_new_cracks':2,'total_cracks':137,'reward_used_for_score':11.2,'score_after':0.5,'runtime_seconds':2.9}).data)
    assert d.state.last_completed_slice['job_id'] == 4
    assert d.state.previous_completed_slice is None
    assert len(d.state.completed_slice_order) == 1


def test_two_jobs_render_distinct_last_previous():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws', scheduler_total_slices=150)
    s.update_scheduler_job(normalize_scheduler_record({'job_id':3,'phase':'warmup','arm':'a','shared_new_cracks':1}).data)
    s.update_scheduler_job(normalize_scheduler_record({'job_id':4,'phase':'warmup','arm':'b','shared_new_cracks':2}).data)
    assert s.previous_completed_slice['job_id'] == 3
    assert s.last_completed_slice['job_id'] == 4


def test_same_job_id_not_counted_twice():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws')
    data=normalize_scheduler_record({'job_id':4,'phase':'warmup','arm':'a','shared_new_cracks':2}).data
    assert s.update_scheduler_job(data)
    assert not s.update_scheduler_job(data)
    assert s.arm_stats['a'].run_count == 1
    assert s.arm_stats['a'].total_new == 2
    assert len(s.completed_slice_order) == 1


def test_update_slice_rejects_non_jobs_jsonl_records():
    s=DashboardState('example.nl','/tmp/ws')
    assert not s.update_slice({'source':'stdout','slice_index':4,'arm':'a','new':2})
    assert s.last_completed_slice is None
    assert s.arm_stats == {}


def test_real_warmup_record_counts_current_schema():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    s=DashboardState('example.nl','/tmp/ws')
    s.update_scheduler_job(normalize_scheduler_record(_real_warmup_record()).data)
    a=s.arm_stats['dict/seclists']
    assert a.run_count == 1
    assert a.total_new == 105 and a.last_new == 105
    assert round(a.last_reward, 2) == 5.60
    assert round(a.last_score, 2) == 0.84
    assert round(a.avg_runtime, 1) == 18.7
    assert a.last_seen_slice == 1


def test_python_deps_ok_does_not_update_stage_message_in_normal_mode():
    from nsec3_recon.events import PipelineEvent
    s=DashboardState(verbose=False)
    s.handle_event(PipelineEvent('now','nsec3map','debug','python_deps_ok','nsec3map Python dependencies available',{}))
    assert all(st.message != 'nsec3map Python dependencies available' for st in s.stages.values())
    assert not any('Python dependencies available' in a['message'] for a in s.recent_activity)


def test_python_deps_ok_visible_or_processed_in_verbose_mode():
    from nsec3_recon.events import PipelineEvent
    s=DashboardState(verbose=True)
    s.handle_event(PipelineEvent('now','nsec3map','debug','python_deps_ok','nsec3map Python dependencies available',{}))
    assert s.stages['nsec3map_enumeration'].message == 'nsec3map Python dependencies available'


def test_low_value_success_warning_still_visible():
    from nsec3_recon.events import PipelineEvent
    s=DashboardState(verbose=False)
    s.handle_event(PipelineEvent('now','nsec3map','warning','python_deps_ok','warn',{}))
    assert any('warn' in a['message'] for a in s.recent_activity)


def test_nsec3map_stage_emits_python_deps_ok_debug():
    text=Path('src/nsec3_recon/stages/nsec3map_stage.py').read_text()
    assert '"python_deps_ok", "nsec3map Python dependencies available", "debug"' in text


def test_render_does_not_show_duplicate_job_slice():
    from nsec3_recon.events import PipelineEvent
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    d=RichDashboard('example.nl','/tmp/ws', scheduler_total_slices=150)
    d.handle_event(PipelineEvent('now','scheduler','info','stdout','[4/150] warmup dict/opentaal_dutch reason=warmup new=2 total=137 reward=11.20 runtime=2.9s',{}))
    d.state.update_scheduler_job(normalize_scheduler_record({'job_id':4,'phase':'warmup','arm':'dict/opentaal_dutch','shared_new_cracks':2,'total_cracks':137,'reward_used_for_score':11.2,'score_after':0.5,'runtime_seconds':2.9}).data)
    out=_render_text(d.state)
    assert out.count('job 4/150') == 1
    assert 'slice 4/150' not in out
    assert 'waiting for previous completed slice' in out


def test_scheduler_record_key_uses_job_prefix_consistently():
    from nsec3_recon.ui.scheduler_parser import normalize_scheduler_record
    r=normalize_scheduler_record({'job_id':1,'phase':'warmup','arm':'dict/seclists','shared_new_cracks':105})
    assert r.data['record_key'] == 'job:1'
