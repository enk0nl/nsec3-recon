import json
import pytest

from nsec3_recon.adapters.nsec3map import detect_command, enumerate_command
from nsec3_recon.config import PipelineConfig
from nsec3_recon.pipeline import Pipeline


def test_nsec3map_enumeration_command_includes_hashlimit(tmp_path):
    cmd = enumerate_command(tmp_path, 'python3', 'example.nl', tmp_path/'zone.txt', 10000)
    assert '--hashlimit=10000' in cmd


def test_nsec3map_detect_only_does_not_receive_hashlimit(tmp_path):
    cmd = detect_command(tmp_path, 'python3', 'example.nl')
    assert not any(arg.startswith('--hashlimit') for arg in cmd)


def test_default_hashlimit_zero_is_reported(tmp_path):
    ctx = Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'run', dry_run=True, dashboard='plain')).run()
    data = json.loads((ctx.workspace.root/'reports/summary.json').read_text())
    assert data['nsec3map_hashlimit'] == 0


def test_positive_hashlimit_is_reported(tmp_path):
    ctx = Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'run', dry_run=True, dashboard='plain', nsec3map_hashlimit=10000)).run()
    data = json.loads((ctx.workspace.root/'reports/summary.json').read_text())
    assert data['nsec3map_hashlimit'] == 10000


def test_nsec3map_hashlimit_not_used_for_axfr_path(monkeypatch, tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage
    monkeypatch.setattr(dns_probe, 'run', lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled': True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr, 'run', lambda ctx: ctx.state.update(axfr={'supported': True}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage, 'detect', lambda ctx: pytest.fail('detect should not run after AXFR'))
    ctx = Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'run', dashboard='plain', nsec3map_hashlimit=10000)).run()
    assert json.loads((ctx.workspace.root/'reports/summary.json').read_text())['completed_via'] == 'axfr'
    assert not (ctx.workspace.root/'nsec3map/map.json').exists()


def test_nsec3map_hashlimit_not_used_for_nsec_zonewalk_path(monkeypatch, tmp_path):
    from nsec3_recon.stages import dns_probe, axfr, nsec3map_stage, scheduler_stage
    monkeypatch.setattr(dns_probe, 'run', lambda ctx: ctx.state.update(dnssec={'probe_dnssec_enabled': True}, nameservers=[]) or ctx.state['dnssec'])
    monkeypatch.setattr(axfr, 'run', lambda ctx: ctx.state.update(axfr={'supported': False}) or ctx.state['axfr'])
    monkeypatch.setattr(nsec3map_stage, 'detect', lambda ctx: ctx.state.update(nsec3map_detect={'status':'success','zone_type':'nsec'}) or ctx.state['nsec3map_detect'])
    def enum(ctx, detected_zone_type=None):
        (ctx.workspace.root/'nsec3map/zone.txt').write_text('www IN NSEC next A\n')
        ctx.state['nsec3map'] = {'zone_type':'nsec','zone_file':'nsec3map/zone.txt','nsec3map_hashlimit':ctx.config.nsec3map_hashlimit}
        return ctx.state['nsec3map']
    monkeypatch.setattr(nsec3map_stage, 'enumerate', enum)
    monkeypatch.setattr(scheduler_stage, 'run', lambda ctx: pytest.fail('scheduler should not run for NSEC'))
    ctx = Pipeline(PipelineConfig('example.nl', out_dir=tmp_path/'run', dashboard='plain', nsec3map_hashlimit=10000)).run()
    assert json.loads((ctx.workspace.root/'reports/summary.json').read_text())['completed_via'] == 'nsec'
