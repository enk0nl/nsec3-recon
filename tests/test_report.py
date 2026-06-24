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
    monkeypatch.setattr(nsec3map_stage,'detect',lambda ctx: ctx.state.update(nsec3map_detect={'status':'success','zone_type':'nsec3'}) or ctx.state['nsec3map_detect'])
    monkeypatch.setattr(nsec3map_stage,'enumerate',lambda ctx, detected_zone_type=None: ctx.state.update(nsec3map={'zone_type':detected_zone_type,'zone_file':'nsec3map/zone.txt'}) or ctx.state['nsec3map'])
    monkeypatch.setattr(hashcatify,'run',lambda ctx: ctx.state.update(hashcatify={'hash_count':1,'hash_file':'nsec3map/h'}) or ctx.state['hashcatify'])
    monkeypatch.setattr(scheduler_stage,'run',lambda ctx: None)
    ctx=Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'r')).run()
    assert json.loads((ctx.workspace.root/'reports/summary.json').read_text())['completed_via']=='nsec3_scheduler'

def test_nsec3_discovered_names_txt_contains_fqdns(tmp_path):
    from nsec3_recon.pipeline import PipelineContext
    from nsec3_recon.config import PipelineConfig
    from nsec3_recon.workspace import Workspace
    from nsec3_recon.events import EventSink
    from nsec3_recon.stages.scheduler_stage import write_discovery_reports
    ws=Workspace.create('example.nl', tmp_path/'r')
    pot=ws.root/'scheduler/run.pot'; pot.parent.mkdir(parents=True, exist_ok=True)
    pot.write_text('h1:\nh2:www\nh3:mail\n')
    ctx=PipelineContext(PipelineConfig('example.nl', out_dir=tmp_path/'r'), ws, EventSink(ws.root/'events.jsonl'))
    write_discovery_reports(ctx)
    lines=(ws.root/'reports/discovered_names.txt').read_text().splitlines()
    assert lines == ['example.nl', 'www.example.nl', 'mail.example.nl']
    assert '@' not in lines and 'www' not in lines and 'mail' not in lines
