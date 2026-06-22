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

def test_dashboard_recovered_candidates_feed(tmp_path):
    p=tmp_path/'x.pot'; p.write_text('h:cand\n')
    d=RichDashboard('example.nl', tmp_path); d.state.current_potfile_path=str(p); d.poll_external_sources(); d.poll_external_sources()
    assert d.state.recovered_candidate_count==1 and d.state.recovered_candidates[0]['candidate']=='cand'

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
    assert capsys.readouterr().out == '' and d.state.current_slice['slice_index']==1

def test_slice_panel_labels_are_completed_slice_labels():
    s=DashboardState('example.nl','/tmp/ws'); s.scheduler_started=True
    import pytest
    Console=pytest.importorskip('rich.console').Console
    console=Console(record=True, width=160, color_system=None); console.print(__import__('nsec3_recon.ui.widgets', fromlist=['build_dashboard']).build_dashboard(s))
    out=console.export_text()
    for h in ('Pipeline','Last completed slice','Previous completed slice','Arm statistics','Recovered candidates','Recent activity'): assert h in out
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
    assert d.state.last_completed_slice['slice_index']==75
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

def test_final_summary_prints_recovered_candidates(monkeypatch, capsys):
    from nsec3_recon import cli
    class Ctx:
        class Workspace:
            class Root:
                def __truediv__(self, other): return '/tmp/summary.json'
            root=Root()
        workspace=Workspace(); state={'summary': {'completed_via': 'nsec3_scheduler'}}
        class Dash:
            class State: recovered_candidate_count=1234
            state=State()
        dashboard_controller=Dash()
    monkeypatch.setattr(cli, 'Pipeline', lambda cfg: type('P', (), {'run': lambda self: Ctx()})())
    assert cli.main(['example.nl','--dashboard','rich']) == 0
    out=capsys.readouterr().out
    assert 'Completed via:' in out and 'Summary:' in out and 'Recovered candidates: 1234' in out

def _render_text(state):
    import pytest
    Console=pytest.importorskip('rich.console').Console
    console=Console(record=True, width=180, height=45, color_system=None)
    console.print(__import__('nsec3_recon.ui.widgets', fromlist=['build_dashboard']).build_dashboard(state))
    return console.export_text()

def test_dashboard_render_contains_key_sections():
    s=DashboardState('example.nl','/tmp/ws'); s.scheduler_started=True
    out=_render_text(s)
    for h in ('Pipeline','Last completed slice','Previous completed slice','Arm statistics','Recovered candidates','Recent activity'): assert h in out

def test_arm_stats_headers_are_readable():
    s=DashboardState('example.nl','/tmp/ws'); s.update_slice({'slice_index':1,'arm':'feedback/predictive-prefix','new':1,'reward':1.2,'runtime_seconds':3.4})
    out=_render_text(s)
    for h in ('Arm','Runs','New','Last','Avg R','Last R','Avg t','Seen'): assert h in out
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

def test_recovered_candidates_have_timestamps():
    s=DashboardState('example.nl','/tmp/ws'); s.current_potfile_path='/tmp/ws/scheduler/run.pot'; s.add_recovered_candidates(['api'])
    out=_render_text(s)
    import re
    assert re.search(r'\d{2}:\d{2}:\d{2}\s+api', out)

def test_recovered_candidates_panel_prominent():
    s=DashboardState('example.nl','/tmp/ws')
    out=_render_text(s)
    assert 'Recovered candidates' in out and 'total=0' in out

def test_recovered_candidate_timestamp_spacing():
    s=DashboardState('example.nl','/tmp/ws')
    s.recovered_candidates.append({'timestamp':'21:07:22','candidate':'www','first_seen_at':0})
    s.recovered_candidate_count=1
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
