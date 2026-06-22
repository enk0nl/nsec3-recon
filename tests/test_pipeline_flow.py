import json, pytest
from pathlib import Path
from nsec3_recon.pipeline import Pipeline, PipelineError
from nsec3_recon.config import PipelineConfig

def pipe(tmp_path): return Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'run', tui=False))

def test_dnssec_disabled_short_circuits(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'dnssec_enabled':False}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'run',lambda ctx: pytest.fail('nsec3map called'))
    ctx=pipe(tmp_path).run(); assert json.loads((ctx.workspace.root/'reports/summary.json').read_text())['completed_via']=='not_dnssec'

def test_axfr_success_short_circuits_pipeline(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'dnssec_enabled':True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':True}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'run',lambda ctx: pytest.fail('called'))
    assert json.loads((pipe(tmp_path).run().workspace.root/'reports/summary.json').read_text())['completed_via']=='axfr'

def test_nsec3_runs_hashcatify_and_scheduler(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage, hashcatify, scheduler_stage
    calls=[]
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'dnssec_enabled':True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'run',lambda ctx: ctx.state.update(nsec3map={'zone_type':'nsec3','zone_file':'nsec3map/zone.txt'}) or ctx.state['nsec3map'])
    monkeypatch.setattr(hashcatify,'run',lambda ctx: calls.append('h') or ctx.state.update(hashcatify={'hash_count':1,'hash_file':'nsec3map/h'}) or ctx.state['hashcatify'])
    monkeypatch.setattr(scheduler_stage,'run',lambda ctx: calls.append('s'))
    pipe(tmp_path).run(); assert calls==['h','s']

def test_nsec_zone_short_circuits_before_scheduler(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage, scheduler_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'dnssec_enabled':True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    def n3(ctx):
        (ctx.workspace.root/'nsec3map/zone.txt').write_text('www IN NSEC next A\n'); ctx.state['nsec3map']={'zone_type':'nsec','zone_file':'nsec3map/zone.txt'}; return ctx.state['nsec3map']
    monkeypatch.setattr(nsec3map_stage,'run',n3); monkeypatch.setattr(scheduler_stage,'run',lambda ctx: pytest.fail('scheduler'))
    assert json.loads((pipe(tmp_path).run().workspace.root/'reports/summary.json').read_text())['completed_via']=='nsec'

def test_stage_failure_writes_failed_summary(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'dnssec_enabled':True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'run',lambda ctx: (_ for _ in ()).throw(PipelineError('nsec3map','boom')))
    with pytest.raises(PipelineError): pipe(tmp_path).run()
    assert json.loads((tmp_path/'run/reports/summary.json').read_text())['completed_via']=='failed'
