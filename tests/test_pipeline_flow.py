import json, pytest
from pathlib import Path
from nsec3_recon.pipeline import Pipeline, PipelineError
from nsec3_recon.config import PipelineConfig


def pipe(tmp_path, tui=False):
    return Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'run', tui=tui))


def test_dnssec_probe_false_does_not_skip_nsec3map_detect(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    calls=[]
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled':False,'dnssec_enabled':False}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: calls.append('detect') or {'status':'not_dnssec','zone_type':'none'})
    ctx=pipe(tmp_path).run()
    assert calls==['detect']
    assert json.loads((ctx.workspace.root/'reports/summary.json').read_text())['completed_via']=='not_dnssec'


def test_not_dnssec_requires_nsec3map_detect_none(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled':False,'dnssec_enabled':False}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: ctx.state.update(nsec3map_detect={'status':'not_dnssec','zone_type':'none'}) or ctx.state['nsec3map_detect'])
    ctx=pipe(tmp_path).run()
    assert json.loads((ctx.workspace.root/'reports/summary.json').read_text())['completed_via']=='not_dnssec'


def test_axfr_success_short_circuits_pipeline(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled':True,'dnssec_enabled':True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':True}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: pytest.fail('called'))
    assert json.loads((pipe(tmp_path).run().workspace.root/'reports/summary.json').read_text())['completed_via']=='axfr'


def test_nsec3_detect_runs_scheduler_even_if_dns_probe_false(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage, hashcatify, scheduler_stage
    calls=[]
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled':False,'dnssec_enabled':False}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: ctx.state.update(nsec3map_detect={'status':'success','zone_type':'nsec3'}) or ctx.state['nsec3map_detect'])
    monkeypatch.setattr(nsec3map_stage,'enumerate',lambda ctx, detected_zone_type=None: ctx.state.update(nsec3map={'zone_type':detected_zone_type,'zone_file':'nsec3map/zone.txt'}) or ctx.state['nsec3map'])
    monkeypatch.setattr(hashcatify,'run',lambda ctx: calls.append('h') or ctx.state.update(hashcatify={'hash_count':1,'hash_file':'nsec3map/h'}) or ctx.state['hashcatify'])
    monkeypatch.setattr(scheduler_stage,'run',lambda ctx: calls.append('s'))
    pipe(tmp_path).run(); assert calls==['h','s']


def test_nsec_detect_stops_before_scheduler_even_if_dns_probe_false(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage, scheduler_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled':False,'dnssec_enabled':False}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: ctx.state.update(nsec3map_detect={'status':'success','zone_type':'nsec'}) or ctx.state['nsec3map_detect'])
    def enum(ctx, detected_zone_type=None):
        (ctx.workspace.root/'nsec3map/zone.txt').parent.mkdir(parents=True, exist_ok=True)
        (ctx.workspace.root/'nsec3map/zone.txt').write_text('www IN NSEC next A\n')
        ctx.state['nsec3map']={'zone_type':'nsec','zone_file':'nsec3map/zone.txt'}; return ctx.state['nsec3map']
    monkeypatch.setattr(nsec3map_stage,'enumerate',enum); monkeypatch.setattr(scheduler_stage,'run',lambda ctx: pytest.fail('scheduler'))
    assert json.loads((pipe(tmp_path).run().workspace.root/'reports/summary.json').read_text())['completed_via']=='nsec'


def test_stage_failure_writes_failed_summary(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled':True,'dnssec_enabled':True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: (_ for _ in ()).throw(PipelineError('nsec3map','boom')))
    with pytest.raises(PipelineError): pipe(tmp_path).run()
    assert json.loads((tmp_path/'run/reports/summary.json').read_text())['completed_via']=='failed'


def test_pipeline_prints_progress_in_no_tui_mode(monkeypatch,tmp_path,capsys):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    def fake_dns(ctx):
        ctx.events.emit('dns_probe','completed','DNS probe completed')
        ctx.state.update(dnssec={'probe_dnssec_enabled':False}, nameservers=[])
        return ctx.state['dnssec']
    def fake_axfr(ctx):
        ctx.events.emit('axfr','axfr_refused','AXFR refused')
        ctx.state.update(axfr={'supported':False})
        return ctx.state['axfr']
    def fake_detect(ctx):
        ctx.events.emit('nsec3map','detect_completed','detected zone_type=none')
        ctx.state.update(nsec3map_detect={'status':'not_dnssec','zone_type':'none'})
        return ctx.state['nsec3map_detect']
    monkeypatch.setattr(dns_probe,'run',fake_dns)
    monkeypatch.setattr(axfr,'run',fake_axfr)
    monkeypatch.setattr(nsec3map_stage,'detect',fake_detect)
    pipe(tmp_path).run()
    out=capsys.readouterr().out
    assert '[dns_probe]' in out and '[axfr]' in out and '[nsec3map]' in out


def test_pipeline_prints_final_summary_path(monkeypatch,tmp_path,capsys):
    from nsec3_recon.cli import main
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled':False}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: ctx.state.update(nsec3map_detect={'status':'not_dnssec','zone_type':'none'}) or ctx.state['nsec3map_detect'])
    assert main(['example.nl','--out-dir',str(tmp_path/'run'),'--no-tui']) == 0
    out=capsys.readouterr().out
    assert 'Completed via:' in out and 'reports/summary.json' in out and 'Workspace:' in out


def test_tui_falls_back_to_console_if_dashboard_not_implemented(monkeypatch,tmp_path,capsys):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    def fake_dns(ctx):
        ctx.events.emit('dns_probe','completed','DNS probe completed')
        ctx.state.update(dnssec={'probe_dnssec_enabled':False}, nameservers=[])
        return ctx.state['dnssec']
    monkeypatch.setattr(dns_probe,'run',fake_dns)
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: ctx.state.update(nsec3map_detect={'status':'not_dnssec','zone_type':'none'}) or ctx.state['nsec3map_detect'])
    pipe(tmp_path, tui=True).run()
    assert '[dns_probe]' in capsys.readouterr().out


def test_summary_separates_dnssec_probe_from_nsec3map_detection(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled':False}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: ctx.state.update(nsec3map_detect={'status':'not_dnssec','zone_type':'none'}) or ctx.state['nsec3map_detect'])
    data=json.loads((pipe(tmp_path).run().workspace.root/'reports/summary.json').read_text())
    assert 'dnssec_probe_enabled' in data and 'nsec3map_detected_zone_type' in data
