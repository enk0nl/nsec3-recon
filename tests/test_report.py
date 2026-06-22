import json
from nsec3_recon.pipeline import Pipeline
from nsec3_recon.config import PipelineConfig

def test_summary_json_written_for_axfr(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'dnssec_enabled':True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':True}) or ctx.state['axfr'])
    ctx=Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r')).run()
    assert json.loads((ctx.workspace.root/'reports/summary.json').read_text())['completed_via']=='axfr'

def test_summary_json_written_for_nsec3_scheduler(monkeypatch,tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage, hashcatify, scheduler_stage
    monkeypatch.setattr(dns_probe,'run',lambda ctx: ctx.state.update(dnssec={'dnssec_enabled':True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr,'run',lambda ctx: ctx.state.update(axfr={'supported':False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage,'run',lambda ctx: ctx.state.update(nsec3map={'zone_type':'nsec3','zone_file':'nsec3map/zone.txt'}) or ctx.state['nsec3map'])
    monkeypatch.setattr(hashcatify,'run',lambda ctx: ctx.state.update(hashcatify={'hash_count':1,'hash_file':'nsec3map/h'}) or ctx.state['hashcatify'])
    monkeypatch.setattr(scheduler_stage,'run',lambda ctx: None)
    ctx=Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r')).run()
    assert json.loads((ctx.workspace.root/'reports/summary.json').read_text())['completed_via']=='nsec3_scheduler'
