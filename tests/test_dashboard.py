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

def test_dashboard_render_contains_key_sections():
    s=DashboardState('example.nl','/tmp/ws'); s.scheduler_started=True
    import pytest
    Console=pytest.importorskip('rich.console').Console
    console=Console(record=True, width=160, color_system=None); console.print(__import__('nsec3_recon.ui.widgets', fromlist=['build_dashboard']).build_dashboard(s))
    out=console.export_text()
    for h in ('Pipeline','Current slice','Previous slice','Arm statistics','Recovered candidates'): assert h in out

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
